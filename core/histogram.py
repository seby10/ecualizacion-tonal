"""
Cómputo de histogramas por canal.
np.bincount es más rápido que np.histogram para datos uint8.
"""
import numpy as np


def histogram_uint8(channel: np.ndarray) -> np.ndarray:
    """
    Devuelve array de 256 enteros con el conteo de cada intensidad.
    """
    if channel.dtype != np.uint8:
        channel = channel.astype(np.uint8)
    return np.bincount(channel.ravel(), minlength=256).astype(np.int64)
