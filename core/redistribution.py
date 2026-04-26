"""
ALGORITMOS DE REDISTRIBUCIÓN TONAL — IMPLEMENTACIÓN MANUAL
==========================================================

Objetivo del trabajo: preprocesar la imagen para que la binarización
posterior separe mejor el objeto del fondo (reconocimiento de objetos).

Técnica principal usada por la GUI:
    * lut_stretch(min_in, max_in)   — contrast stretching (estiramiento lineal)

Técnicas adicionales documentadas en este módulo (no usadas por la GUI,
sirven como referencia académica para defender el conocimiento del tema):
    * lut_equalize(channel, strength)  — ecualización de histograma manual.
    * lut_gamma(strength)              — corrección gamma manual.

NO se usan funciones "de alto nivel" de librerías para la redistribución:
sin `cv2.equalizeHist`, sin `cv2.normalize`, sin `skimage.exposure.*`.
Solo aritmética básica de NumPy.

Cada función devuelve una LUT (Look-Up Table) de 256 entradas uint8:
para una intensidad de entrada `v`, `lut[v]` es la intensidad de salida.
"""
from __future__ import annotations
import numpy as np


# =====================================================================
# 1. Histograma y CDF (cálculos auxiliares)
# =====================================================================

def compute_histogram(channel: np.ndarray) -> np.ndarray:
    """
    Cuenta cuántos píxeles tienen cada intensidad 0..255.

    Equivalente a:
        hist = [0] * 256
        for v in channel.ravel():
            hist[v] += 1
    """
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


# =====================================================================
# 2. Contrast stretching — TÉCNICA PRINCIPAL
# =====================================================================
#
# Definición clásica (Gonzalez & Woods, "Digital Image Processing", §3.2):
#
#     ┌─ 0                                        si x < min_in
# y = ┤  (x − min_in) / (max_in − min_in) · 255    si min_in ≤ x ≤ max_in
#     └─ 255                                       si x > max_in
#
# Interpretación:
#   * Selecciona una "ventana" de intensidades [min_in, max_in].
#   * Estira esa ventana hasta cubrir todo el rango [0, 255].
#   * Valores fuera de la ventana se saturan (clipping intencional).
#
# Ventajas para el preprocesamiento previo a binarización:
#   * Si min_in se elige como el "piso de ruido", todo el ruido se va a 0.
#   * Si max_in se elige como la saturación, las luces extremas se van a 255.
#   * El rango útil queda con contraste máximo → la binarización separa
#     trivialmente objeto vs. fondo.
#
# La operación ES una redistribución de píxeles: reorganiza la masa del
# histograma estirándola linealmente sobre [0, 255].
#
# Propiedades:
#   * Monótona (si min_in < max_in).
#   * No genera bandas, no overshoot.
#   * Pierde información fuera de la ventana — feature, no bug.
# =====================================================================

def lut_stretch(min_in: int, max_in: int) -> np.ndarray:
    """
    Construye la LUT de contrast stretching.
    Implementación a mano: 4 líneas de aritmética NumPy, sin librerías
    de alto nivel.
    """
    min_in = int(np.clip(min_in, 0, 255))
    max_in = int(np.clip(max_in, 0, 255))

    # caso degenerado: ventana inválida → LUT identidad (sin cambios)
    if max_in <= min_in:
        return np.arange(256, dtype=np.uint8)

    x = np.arange(256, dtype=np.float64)
    y = (x - min_in) / (max_in - min_in) * 255.0
    y = np.clip(y, 0.0, 255.0)
    return np.round(y).astype(np.uint8)


# =====================================================================
# 3. Ecualización de histograma (alternativa documentada)
# =====================================================================
#
# Algoritmo (Gonzalez & Woods, §3.3):
#   1. Histograma h[v] del canal.
#   2. CDF: F[v] = Σ h[0..v].
#   3. F_min = primera CDF > 0.
#   4. T[v] = (F[v] − F_min) / (N − F_min) · 255.
#   5. Mezcla con identidad según `strength` (0=identidad, 1=ecualizado).
#
# Diferencia con stretching: es DATA-DRIVEN. La curva depende del histograma
# del canal de entrada — aplana picos automáticamente, sin que el usuario
# elija ventana.
# =====================================================================

def lut_equalize(channel: np.ndarray, strength: float = 1.0) -> np.ndarray:
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


# =====================================================================
# 4. Corrección gamma (alternativa documentada)
# =====================================================================
#
# y = x^γ  en [0, 1], con γ = 4^(−s) y s ∈ [−1, 1].
# Diferencia con stretching: NO clippea — preserva extremos. Suaviza no
# linealmente. Útil cuando no se quiere perder información fuera del rango
# útil.
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
