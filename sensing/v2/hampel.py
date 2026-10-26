"""Hampel filter for robust outlier detection and replacement.

The Hampel filter uses a sliding window of historical samples to compute
the median and Median Absolute Deviation (MAD). Samples deviating by more
than threshold * 1.4826 * MAD from the window median are identified as
anomalies (e.g. microwave interference, single-packet RF collision, dropped frame)
and clamped to the local median.
"""

from collections import deque
import numpy as np


class HampelFilter:
    """Sliding-window Hampel filter supporting scalars and 1D numpy vectors."""

    def __init__(self, window_size: int = 5, n_sigmas: float = 3.0):
        if window_size < 3:
            raise ValueError("window_size must be at least 3")
        self.window_size = int(window_size)
        self.n_sigmas = float(n_sigmas)
        self.buffer = deque(maxlen=self.window_size)

    def reset(self):
        self.buffer.clear()

    def filter(self, values: np.ndarray | float | int) -> np.ndarray:
        """Filter incoming values. Returns cleaned numpy array."""
        arr = np.asarray(values, dtype=float)
        is_scalar = arr.ndim == 0
        if is_scalar:
            arr = arr.reshape(1)

        self.buffer.append(arr.copy())
        if len(self.buffer) < 3:
            return arr.item() if is_scalar else arr

        # Stack history into a 2D array of shape (samples, channels)
        stack = np.stack(list(self.buffer), axis=0)
        med = np.median(stack, axis=0)
        mad = 1.4826 * np.median(np.abs(stack - med), axis=0)
        # Floor mad to avoid zero-division on flat signals (e.g. 0.1 dBm floor)
        mad = np.maximum(mad, 0.1)

        diff = np.abs(arr - med)
        outliers = diff > (self.n_sigmas * mad)

        clean = arr.copy()
        clean[outliers] = med[outliers]

        return clean.item() if is_scalar else clean
