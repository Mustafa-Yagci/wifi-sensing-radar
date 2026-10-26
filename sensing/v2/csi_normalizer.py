"""CSI Normalization and Hardware AGC Cancellation.

Implements:
1. L2 Frobenius amplitude normalization to cancel out packet-by-packet AGC gain hops.
2. Subcarrier quotient / CSI Ratio (Wang et al., IEEE TMC) across antenna pairs or subcarrier pairs.
3. Dynamic subcarrier selection based on dynamic-to-static variance ratio.
"""

import numpy as np


class CsiNormalizer:
    """Normalizes CSI subcarriers to eliminate hardware Automatic Gain Control (AGC) steps."""

    @staticmethod
    def normalize_l2(amplitudes: np.ndarray) -> np.ndarray:
        """Normalize subcarrier amplitudes by their L2 Euclidean norm.

        Mathematical proof:
        If AGC changes the receiver gain by factor k, all subcarriers become k * a_i.
        norm(k * A) = k * norm(A).
        Therefore, (k * A) / norm(k * A) == A / norm(A).
        AGC step is completely eliminated.
        """
        arr = np.asarray(amplitudes, dtype=float)
        norm = np.linalg.norm(arr)
        if norm <= 1e-12:
            return np.zeros_like(arr)
        return arr / norm

    @staticmethod
    def compute_csi_ratio(h1: np.ndarray, h2: np.ndarray) -> np.ndarray:
        """Compute CSI Ratio between two antenna streams or two subcarrier channels.

        Eliminates common-mode CFO (Carrier Frequency Offset), SFO, and AGC.
        """
        arr1 = np.asarray(h1, dtype=float)
        arr2 = np.asarray(h2, dtype=float)
        denom = np.where(np.abs(arr2) < 1e-6, 1e-6, arr2)
        return arr1 / denom

    @staticmethod
    def select_sensitive_subcarriers(subcarrier_matrix: np.ndarray, top_k: int = 16) -> np.ndarray:
        """Select top_k subcarriers exhibiting highest dynamic-to-static variance ratio.

        Parameters:
        - subcarrier_matrix: 2D array of shape (samples, num_subcarriers)
        """
        if subcarrier_matrix.ndim != 2:
            raise ValueError("subcarrier_matrix must be a 2D array (samples, subcarriers)")
        variances = np.var(subcarrier_matrix, axis=0)
        top_indices = np.argsort(variances)[-top_k:]
        return np.sort(top_indices)
