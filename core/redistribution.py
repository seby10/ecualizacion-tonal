"""
ALGORITMOS DE REDISTRIBUCIÓN TONAL — IMPLEMENTACIÓN MANUAL
==========================================================

Objetivo del trabajo: preprocesar la imagen para que la binarización
posterior separe mejor el objeto del fondo (reconocimiento de objetos).

Técnica principal usada por la GUI:
    * lut_remap(from_min, from_max, to_min, to_max)
      Redistribución de rango sin pérdida de píxeles:
      los píxeles en [from_min, from_max] se interpolan linealmente
      hacia [to_min, to_max]; el resto queda en identidad.

Técnicas adicionales documentadas en este módulo (referencia académica):
    * lut_stretch(min_in, max_in)   — contrast stretching (clipping).
    * lut_equalize(channel, strength)  — ecualización de histograma manual.
    * lut_gamma(strength)              — corrección gamma manual.

NO se usan funciones "de alto nivel" de librerías para la redistribución:
sin `cv2.equalizeHist`, sin `cv2.normalize`, sin `skimage.exposure.*`.
Solo aritmética básica de NumPy.

Cada función devuelve una LUT (Look-Up Table) de 256 entradas uint8.
"""
from __future__ import annotations
import numpy as np


# =====================================================================
# 1. Histograma y CDF (cálculos auxiliares)
# =====================================================================

def compute_histogram(channel: np.ndarray) -> np.ndarray:
    flat = channel.ravel().astype(np.uint8, copy=False)
    return np.bincount(flat, minlength=256).astype(np.int64)


def compute_cdf(hist: np.ndarray) -> np.ndarray:
    cdf = np.zeros(256, dtype=np.int64)
    accum = 0
    for v in range(256):
        accum += int(hist[v])
        cdf[v] = accum
    return cdf


# =====================================================================
# 2. Remapeo de rango — TÉCNICA PRINCIPAL
# =====================================================================
#
# Objetivo: mover los píxeles del rango [from_min, from_max] del
# histograma original al rango [to_min, to_max] del histograma de salida,
# usando interpolación lineal. El resto de intensidades NO se toca
# (identidad).
#
# Fórmula para x en [from_min, from_max]:
#   t = (x - from_min) / (from_max - from_min)   ← posición normalizada [0,1]
#   y = to_min + t * (to_max - to_min)            ← interpolación lineal
#
# Para x fuera de [from_min, from_max]:
#   y = x   (identidad)
#
# Propiedad clave: NO se pierden píxeles.
# La masa del histograma se conserva — solo cambia de posición.
# =====================================================================

def lut_remap(from_min: int, from_max: int,
              to_min: int,   to_max: int) -> np.ndarray:
    """
    Construye la LUT de remapeo de rango.
    Los píxeles en [from_min, from_max] se redistribuyen a [to_min, to_max].
    El resto queda en identidad.
    """
    from_min = int(np.clip(from_min, 0, 255))
    from_max = int(np.clip(from_max, 0, 255))
    to_min   = int(np.clip(to_min,   0, 255))
    to_max   = int(np.clip(to_max,   0, 255))

    # LUT base: identidad
    lut = np.arange(256, dtype=np.float64)

    # caso degenerado: ventana de entrada inválida
    if from_max <= from_min:
        return lut.astype(np.uint8)

    # aplicar interpolación solo al rango [from_min, from_max]
    xs = np.arange(from_min, from_max + 1, dtype=np.float64)
    t  = (xs - from_min) / (from_max - from_min)   # [0, 1]
    ys = to_min + t * (to_max - to_min)             # interpolación lineal
    lut[from_min:from_max + 1] = np.clip(np.round(ys), 0, 255)

    return lut.astype(np.uint8)


# =====================================================================
# 3. Contrast stretching (referencia académica — clipping intencional)
# =====================================================================

def lut_stretch(min_in: int, max_in: int) -> np.ndarray:
    min_in = int(np.clip(min_in, 0, 255))
    max_in = int(np.clip(max_in, 0, 255))
    if max_in <= min_in:
        return np.arange(256, dtype=np.uint8)
    x = np.arange(256, dtype=np.float64)
    y = (x - min_in) / (max_in - min_in) * 255.0
    return np.clip(np.round(y), 0, 255).astype(np.uint8)


# =====================================================================
# 4. Ecualización de histograma (referencia académica)
# =====================================================================

def lut_equalize(channel: np.ndarray, strength: float = 1.0) -> np.ndarray:
    s = float(np.clip(strength, 0.0, 1.0))
    N = int(channel.size)
    if N == 0:
        return np.arange(256, dtype=np.uint8)
    hist = compute_histogram(channel)
    cdf  = compute_cdf(hist)
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


# =====================================================================
# 5. Corrección gamma (referencia académica)
# =====================================================================

_GAMMA_BASE = 4.0


def gamma_from_strength(strength: float) -> float:
    s = float(np.clip(strength, -1.0, 1.0))
    return _GAMMA_BASE ** (-s)


def lut_gamma(strength: float) -> np.ndarray:
    g = gamma_from_strength(strength)
    x = np.arange(256, dtype=np.float64) / 255.0
    y = np.power(x, g)
    return np.clip(np.round(y * 255.0), 0, 255).astype(np.uint8)