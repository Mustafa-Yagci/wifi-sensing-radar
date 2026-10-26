"""Comprehensive test suite for sensing.v2 stability modules.

Verifies:
1. Hampel filter spike rejection (single-packet drops/glitches)
2. Dual-rate dynamic baseline tracking under slow thermal drift (v1 fails, v2 adapts)
3. Genuine sustained motion detection preservation
4. CSI L2 normalization immunity to AGC hardware gain hops
5. Butterworth IIR bandpass filtering of human motion frequencies
6. TrafficPacer start/stop lifecycle
"""

import time
import numpy as np
import pytest

from sensing.detector import ChangeDetector as ChangeDetectorV1
from sensing.v2 import (
    HampelFilter,
    AdaptiveChangeDetector,
    CsiNormalizer,
    ButterworthBandpass,
    TrafficPacer,
)


def test_hampel_filter_rejects_spikes():
    hf = HampelFilter(window_size=5, n_sigmas=3.0)
    # Steady signal at -40 dBm
    for _ in range(5):
        clean = hf.filter(-40.0)
        assert abs(clean - (-40.0)) < 1e-3

    # Inject a violent -80 dBm single-frame spike (e.g. microwave glitch)
    spike_result = hf.filter(-80.0)
    # Hampel should replace -80.0 with the local window median (-40.0)
    assert abs(spike_result - (-40.0)) < 1.0


def test_hampel_filter_multichannel_vector():
    hf = HampelFilter(window_size=5, n_sigmas=3.0)
    steady = np.array([-40.0, -45.0, -50.0])
    for _ in range(5):
        hf.filter(steady)

    # Spike only in channel 1
    glitch = np.array([-40.0, -85.0, -50.0])
    cleaned = hf.filter(glitch)
    assert abs(cleaned[1] - (-45.0)) < 1.0
    assert abs(cleaned[0] - (-40.0)) < 1e-3


def test_v1_detector_fails_on_thermal_drift():
    """Prove that v1 ChangeDetector locks into false 'signal_change' when signal drifts slowly."""
    det_v1 = ChangeDetectorV1(calibration_seconds=1.0, window_seconds=1.0)
    t = 0.0

    # 1. Calibration phase at -40 dBm
    for _ in range(35):
        det_v1.update({'source': 'native', 'link_id': 'ap1', 'channel': 6, 'rssi_dbm': -40.0}, t)
        t += 0.1

    assert det_v1.center is not None

    # 2. Simulate 4 dB thermal drift over 30 seconds (quiet room, but temperature rose)
    # -40.0 dBm -> -44.0 dBm
    drift_rssis = np.linspace(-40.0, -44.0, 300)
    states = []
    for val in drift_rssis:
        res = det_v1.update({'source': 'native', 'link_id': 'ap1', 'channel': 6, 'rssi_dbm': float(val)}, t)
        states.append(res['state'])
        t += 0.1

    # v1 detector has a static center of -40 dBm, so at -44 dBm it permanently triggers
    assert 'signal_change' in states[-20:]
    assert det_v1.active is True  # Falsely locked!


def test_v2_adaptive_detector_adapts_to_thermal_drift():
    """Prove that v2 AdaptiveChangeDetector smoothly tracks thermal drift without false triggers."""
    det_v2 = AdaptiveChangeDetector(calibration_seconds=1.0, window_seconds=1.0, drift_alpha=0.02)
    t = 0.0

    # 1. Calibration phase at -40 dBm
    for _ in range(35):
        det_v2.update({'source': 'native', 'link_id': 'ap1', 'channel': 6, 'rssi_dbm': -40.0}, t)
        t += 0.1

    assert det_v2.center is not None

    # 2. Simulate same 4 dB thermal drift over 300 samples
    drift_rssis = np.linspace(-40.0, -44.0, 300)
    states = []
    for val in drift_rssis:
        res = det_v2.update({'source': 'native', 'link_id': 'ap1', 'channel': 6, 'rssi_dbm': float(val)}, t)
        states.append(res['state'])
        t += 0.1

    # v2 tracks the drift and remains quiet!
    assert det_v2.active is False
    assert states[-1] == 'quiet'
    assert abs(det_v2.center[0] - (-44.0)) < 0.8  # Center adapted!


def test_v2_detects_genuine_sustained_motion():
    """Verify that when real sustained human motion occurs, v2 detects it and freezes baseline update."""
    det_v2 = AdaptiveChangeDetector(calibration_seconds=1.0, window_seconds=1.0, drift_alpha=0.01)
    t = 0.0

    # Calibration at -40 dBm
    for _ in range(35):
        det_v2.update({'source': 'native', 'link_id': 'ap1', 'channel': 6, 'rssi_dbm': -40.0}, t)
        t += 0.1

    center_before_motion = float(det_v2.center[0])

    # Sudden human motion: -32 dBm for 2 seconds (> 0.6s sustained threshold)
    detected_states = []
    for _ in range(25):
        res = det_v2.update({'source': 'native', 'link_id': 'ap1', 'channel': 6, 'rssi_dbm': -32.0}, t)
        detected_states.append(res['state'])
        t += 0.1

    # Motion is correctly detected
    assert 'signal_change' in detected_states
    assert det_v2.active is True
    # Baseline was frozen during motion
    center_during_motion = float(det_v2.center[0])
    assert abs(center_during_motion - center_before_motion) < 0.2


def test_csi_normalizer_cancels_agc_step():
    """Verify that a uniform AGC hardware gain hop is eliminated by L2 normalization."""
    # 52 subcarriers
    base_csi = np.random.uniform(10.0, 50.0, size=52)
    norm1 = CsiNormalizer.normalize_l2(base_csi)

    # Sudden AGC jump: all subcarriers multiplied by 2.5x (common gain hop)
    agc_jump_csi = base_csi * 2.5
    norm2 = CsiNormalizer.normalize_l2(agc_jump_csi)

    # Normalized vectors must be identical!
    assert np.allclose(norm1, norm2, atol=1e-10)


def test_csi_ratio_computation():
    h1 = np.array([10.0, 20.0, 30.0])
    h2 = np.array([5.0, 10.0, 15.0])
    ratio = CsiNormalizer.compute_csi_ratio(h1, h2)
    assert np.allclose(ratio, [2.0, 2.0, 2.0], atol=1e-5)


def test_butterworth_bandpass():
    bp = ButterworthBandpass(lowcut=0.1, highcut=4.0, fs=10.0, order=2)
    t = np.arange(0, 20, 0.1)  # 20 seconds at 10 Hz

    # DC drift signal (0.01 Hz)
    dc_drift = 5.0 * np.sin(2 * np.pi * 0.01 * t)
    filtered_dc = bp.filter_batch(dc_drift)
    # 0.01 Hz should be heavily attenuated
    assert np.std(filtered_dc[50:]) < 0.2 * np.std(dc_drift)

    # Human motion signal (1.5 Hz)
    bp.reset()
    motion_sig = 5.0 * np.sin(2 * np.pi * 1.5 * t)
    filtered_motion = bp.filter_batch(motion_sig)
    # 1.5 Hz should pass through strongly
    assert np.std(filtered_motion[50:]) > 0.8 * np.std(motion_sig)


def test_traffic_pacer_lifecycle():
    pacer = TrafficPacer(target_ip="127.0.0.1", port=18888, rate_hz=50.0)
    pacer.start()
    time.sleep(0.1)
    assert pacer.packets_sent > 1
    pacer.stop()
    sent_after_stop = pacer.packets_sent
    time.sleep(0.05)
    assert pacer.packets_sent == sent_after_stop
