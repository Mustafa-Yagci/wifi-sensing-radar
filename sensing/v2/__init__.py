"""WiFi Sensing v2: High-Stability Signal Processing Pipeline.

Modules:
- HampelFilter: Sliding-window median outlier rejection
- AdaptiveChangeDetector: Dual-rate dynamic baseline tracking (thermal drift immunity)
- CsiNormalizer: Subcarrier ratio & L2 normalization (AGC step cancellation)
- ButterworthBandpass: 4th-order IIR bandpass filter (0.1 - 4.0 Hz human band)
- TrafficPacer: Lightweight active UDP keep-alive to defeat driver sleep
"""

from .hampel import HampelFilter
from .adaptive_detector import AdaptiveChangeDetector
from .csi_normalizer import CsiNormalizer
from .butterworth import ButterworthBandpass
from .traffic_pacer import TrafficPacer

__all__ = [
    'HampelFilter',
    'AdaptiveChangeDetector',
    'CsiNormalizer',
    'ButterworthBandpass',
    'TrafficPacer',
]
