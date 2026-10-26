"""Adaptive Change Detector with Dynamic Baseline and Outlier Suppression (v2).

Key Innovations over v1:
1. Integrated Hampel filtering to reject single-sample RF spikes and packet drop anomalies.
2. Dual-rate dynamic baseline tracking:
   - When QUIET: Slowly adapts center and noise baseline (alpha ~ 0.005) to track thermal
     drift and ambient RF fluctuations over hours/days.
   - When TRIGGERED: Freezes baseline update immediately so genuine human motion is never
     absorbed into the baseline.
3. L2 norm scaling for CSI amplitudes to cancel packet-by-packet hardware AGC steps.
4. Preserves 100% interface compatibility with v1 ChangeDetector.
"""

from collections import deque
import math
import numpy as np

from .hampel import HampelFilter
from .csi_normalizer import CsiNormalizer


class AdaptiveChangeDetector:
    """v2 Robust Change Detector with dynamic baseline and outlier immunity."""

    def __init__(self, calibration_seconds=20.0, window_seconds=2.0, lock_calibration=False,
                 drift_alpha=0.005, enable_hampel=True):
        self.calibration_seconds = float(calibration_seconds)
        self.window_seconds = float(window_seconds)
        self.lock_calibration = bool(lock_calibration)
        self.drift_alpha = float(drift_alpha)
        self.enable_hampel = bool(enable_hampel)
        self.hampel = HampelFilter(window_size=5, n_sigmas=3.0) if enable_hampel else None
        self.reset()

    def reset(self):
        self.history = deque(maxlen=2000)
        self.baseline = []
        self.started = None
        self.center = None
        self.noise = None
        self.source_key = None
        self.last_time = None
        self.candidate_since = None
        self.quiet_since = None
        self.active = False
        self.events = 0
        self.last_channel_z = None
        self.last_was_csi = False
        self.outlier_count = 0
        self.drift_adjustments = 0
        if self.hampel:
            self.hampel.reset()

    def update(self, sample, now):
        is_csi = sample.get('amplitudes') is not None
        if is_csi:
            values = np.asarray(sample['amplitudes'], dtype=float)
        else:
            links = [link for link in sample.get('links') or [] if link.get('rssi_dbm') is not None]
            values = np.asarray([sample['rssi_dbm']] + [link['rssi_dbm'] for link in links], dtype=float)

        if values.ndim != 1 or not len(values) or not np.all(np.isfinite(values)):
            raise ValueError('Sensor values must be a finite vector')

        # AGC Step Elimination for CSI
        if is_csi:
            scale = float(np.mean(values))
            if scale <= 0:
                raise ValueError('CSI frame contains no signal')
            values = CsiNormalizer.normalize_l2(values)

        # Hampel Outlier Filter
        if self.hampel:
            clean_values = self.hampel.filter(values)
            if not np.allclose(clean_values, values, atol=1e-3):
                self.outlier_count += 1
            values = clean_values

        # Calibration lock / Link change detection
        if self.lock_calibration and self.center is not None:
            link_changed = (self.source_key is not None and (
                sample['source'] != self.source_key[0] or
                sample.get('link_id') != self.source_key[1] or
                sample.get('channel') != self.source_key[2]
            ))
            if link_changed:
                self.reset()
                self.source_key = (sample['source'], sample.get('link_id'), sample.get('channel'), len(values))
            else:
                target_len = len(self.center)
                if len(values) > target_len:
                    values = values[:target_len]
                elif len(values) < target_len:
                    values = np.concatenate([values, self.center[len(values):]])
        else:
            key = (sample['source'], sample.get('link_id'), sample.get('channel'), len(values))
            if key != self.source_key or (self.last_time is not None and now - self.last_time > 3):
                self.reset()
                self.source_key = key

        if self.last_time is not None and now <= self.last_time:
            raise ValueError('Samples must be ordered by acquisition time')
        self.last_time = now

        if self.started is None:
            self.started = now

        self.history.append((now, values))
        while self.history and now - self.history[0][0] > self.window_seconds:
            self.history.popleft()

        progress = min(1.0, (now - self.started) / self.calibration_seconds)

        # Initial Calibration Stage
        if self.center is None:
            self.baseline.append(values)
            progress = min(progress, len(self.baseline) / 30)
            if progress >= 1:
                baseline = np.stack(self.baseline)
                self.center = np.median(baseline, axis=0)
                floor = 0.015 if is_csi else 1.0
                self.noise = np.maximum(1.4826 * np.median(np.abs(baseline - self.center), axis=0), floor)
                self.baseline = []
            return self.result('calibrating', progress, 0.0)

        recent = np.stack([value for _, value in self.history])
        excursion = np.percentile(np.abs(recent - self.center), 75, axis=0)
        spread = 1.4826 * np.median(np.abs(recent - np.median(recent, axis=0)), axis=0)
        channel_z = np.maximum(excursion, spread) / self.noise

        if is_csi:
            z = float(np.median(channel_z))
        elif channel_z.size > 1:
            z = float(max(channel_z[0], 0.9 * float(np.median(channel_z[1:]))))
        else:
            z = float(channel_z[0])

        self.last_channel_z = channel_z
        self.last_was_csi = is_csi
        score = min(100.0, max(0.0, z / 6.0 * 100.0))

        # State Transition Logic with Hysteresis
        if z >= 3.0:
            self.quiet_since = None
            if self.candidate_since is None:
                self.candidate_since = now
            if now - self.candidate_since >= 0.6 and not self.active:
                self.active = True
                self.events += 1
        else:
            self.candidate_since = None
            if self.active and z < 1.8:
                if self.quiet_since is None:
                    self.quiet_since = now
                if now - self.quiet_since >= 2.0:
                    self.active = False
            else:
                self.quiet_since = None

        # DUAL-RATE DYNAMIC BASELINE ADAPTATION
        # When confirmed quiet (not active and z-score low), adapt baseline to follow thermal drift
        if not self.active and z < 1.8:
            recent_med = np.median(recent, axis=0)
            self.center = (1.0 - self.drift_alpha) * self.center + self.drift_alpha * recent_med
            floor = 0.015 if is_csi else 1.0
            recent_noise = np.maximum(1.4826 * np.median(np.abs(recent - recent_med), axis=0), floor)
            self.noise = (1.0 - self.drift_alpha) * self.noise + self.drift_alpha * recent_noise
            self.drift_adjustments += 1

        state = 'motion_candidate' if is_csi and self.active else 'signal_change' if self.active else 'quiet'
        return self.result(state, 1.0, score)

    def result(self, state, progress, score):
        times = [row[0] for row in self.history]
        rate = (len(times) - 1) / (times[-1] - times[0]) if len(times) > 1 else 0.0
        links = None
        if self.last_channel_z is not None and not self.last_was_csi and self.last_channel_z.size > 1:
            links = [round(min(100.0, max(0.0, float(z) / 6.0 * 100.0)), 1) for z in self.last_channel_z]
        return {
            'state': state, 'learning_progress': round(progress, 3),
            'change_score': round(score, 1), 'motion_detected': self.active,
            'is_calibrated': self.center is not None,
            'read_rate_hz': round(rate, 2) if math.isfinite(rate) else 0,
            'event_count': self.events,
            'baseline_rssi_dbm': round(float(self.center[0]), 1)
            if self.center is not None and len(self.center) >= 1 else None,
            'link_change': links,
            'engine_version': 'v2',
            'outliers_suppressed': self.outlier_count,
            'drift_adjustments': self.drift_adjustments,
        }
