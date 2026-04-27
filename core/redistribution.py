"""
Algoritmos de redistribución tonal (Implementación manual).
Incluye Contrast Stretching, Ecualización de histograma y Corrección gamma.
No se utilizan librerías de alto nivel para estos cálculos.
"""
from __future__ import annotations
import numpy as np


# Histograma y CDF
def compute_histogram(channel: np.ndarray) -> np.ndarray:
    """Cuenta frecuencias de intensidad (0..255)."""
    flat = channel.ravel().astype(np.uint8, copy=False)
    return np.bincount(flat, minlength=256).astype(np.int64)


def compute_cdf(hist: np.ndarray) -> np.ndarray:
    """CDF discreta: F[v] = h[0] + h[1] + ... + h[v]."""
    cdf = np.zeros(256, dtype=np.int64)
    accum = 0
    for v in range(256):
        accum += int(hist[v])
        cdf[v] = accum
    return cdf


# Contrast stretching
def lut_stretch(min_in: int, max_in: int) -> np.ndarray:
    """LUT de contrast stretching lineal (ventana [min_in, max_in] a [0, 255])."""
    min_in = int(np.clip(min_in, 0, 255))
    max_in = int(np.clip(max_in, 0, 255))

    # caso degenerado: ventana inválida → LUT identidad (sin cambios)
    if max_in <= min_in:
        return np.arange(256, dtype=np.uint8)

    x = np.arange(256, dtype=np.float64)
    y = (x - min_in) / (max_in - min_in) * 255.0
    y = np.clip(y, 0.0, 255.0)
    return np.round(y).astype(np.uint8)


# Ecualización de histograma
def lut_equalize(channel: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """LUT de ecualización de histograma manual mezclada según strength."""
    s = float(np.clip(strength, 0.0, 1.0))
    N = int(channel.size)
    if N == 0:
        return np.arange(256, dtype=np.uint8)

    hist = compute_histogram(channel)
    cdf = compute_cdf(hist)

    cdf_min = 0
    for v in range(256):
        if cdf[v] > 0:
            cdf_min = int(cdf[v])
            break

    eq = np.zeros(256, dtype=np.float64)
    denom = N - cdf_min
    if denom > 0:
        for v in range(256):
            eq[v] = (cdf[v] - cdf_min) / denom * 255.0
    else:
        eq[:] = float(np.argmax(hist))

    identity = np.arange(256, dtype=np.float64)
    blended = (1.0 - s) * identity + s * eq
    return np.clip(np.round(blended), 0, 255).astype(np.uint8)


# Corrección gamma


_GAMMA_BASE = 4.0


def gamma_from_strength(strength: float) -> float:
    s = float(np.clip(strength, -1.0, 1.0))
    return _GAMMA_BASE ** (-s)


def lut_gamma(strength: float) -> np.ndarray:
    g = gamma_from_strength(strength)
    x = np.arange(256, dtype=np.float64) / 255.0
    y = np.power(x, g)
    return np.clip(np.round(y * 255.0), 0, 255).astype(np.uint8)
