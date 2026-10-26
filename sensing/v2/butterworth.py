"""Butterworth IIR Bandpass Filter for Human Motion Isolation.

Isolates human activity frequencies (0.1 Hz to 4.0 Hz) while rejecting:
- Thermal DC drift (< 0.05 Hz)
- High-frequency RF noise and spurious switching (> 5.0 Hz)

Uses Second-Order Sections (SOS) for numerical stability with streaming state tracking.
"""

import numpy as np
from scipy.signal import butter, sosfilt, sosfilt_zi


class ButterworthBandpass:
    """Online streaming 4th-order Butterworth bandpass filter."""

    def __init__(self, lowcut: float = 0.1, highcut: float = 4.0, fs: float = 10.0, order: int = 4):
        self.fs = float(fs)
        self.lowcut = float(lowcut)
        self.highcut = float(highcut)
        self.order = int(order)

        # Nyquist frequency
        nyq = 0.5 * self.fs
        low = self.lowcut / nyq
        high = min(self.highcut / nyq, 0.99)

        if low <= 0 or high >= 1 or low >= high:
            raise ValueError(f"Invalid cutoff frequencies for fs={fs}: [{lowcut}, {highcut}]")

        self.sos = butter(self.order, [low, high], btype='bandpass', output='sos')
        self.zi = None
        self.reset()

    def reset(self):
        """Reset internal filter state."""
        self.zi = None

    def filter_sample(self, value: float) -> float:
        """Filter a single incoming scalar in real time."""
        if self.zi is None:
            self.zi = sosfilt_zi(self.sos) * value
        y, self.zi = sosfilt(self.sos, [value], zi=self.zi)
        return float(y[0])

    def filter_batch(self, values: np.ndarray) -> np.ndarray:
        """Filter a 1D batch of historical values."""
        arr = np.asarray(values, dtype=float)
        if len(arr) == 0:
            return arr
        zi = sosfilt_zi(self.sos) * arr[0]
        y, _ = sosfilt(self.sos, arr, zi=zi)
        return y
