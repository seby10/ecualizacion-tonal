"""
Curva de transferencia tonal con un único parámetro: `strength`.

Formulación:
    s ∈ [-1, 1]           (posición del slider, centrada en 0)
    γ = 4^(-s)            → γ ∈ [0.25, 4]    (s=0 ⇒ γ=1, identidad)
    y = x^γ               con x normalizado en [0, 1]

Propiedades matemáticas garantizadas:
  * Monótona creciente (derivada γ·x^(γ−1) ≥ 0 para x ∈ [0,1], γ > 0).
  * Anclada en (0,0) y (1,1) → 0^γ = 0, 1^γ = 1. Ningún valor extremo se
    pierde por saturación ni recorte.
  * C∞ en (0,1]. Redistribución suave, sin bandas ni escalones.
  * Interpretación del slider:
        s > 0 → γ < 1 → redistribuye hacia altos (aclara y expande luces).
        s < 0 → γ > 1 → redistribuye hacia bajos (oscurece y expande sombras).
"""
from dataclasses import dataclass
import numpy as np


# factor del mapeo s → γ. 4 da un rango cómodo y simétrico.
_GAMMA_BASE = 4.0


@dataclass
class ToneParams:
    strength: float = 0.0  # en [-1, 1]; 0 es identidad


def gamma_from_strength(strength: float) -> float:
    s = float(np.clip(strength, -1.0, 1.0))
    return _GAMMA_BASE ** (-s)


def tone_map(x: np.ndarray, params: ToneParams) -> np.ndarray:
    """
    Aplica la curva tonal a un array normalizado en [0, 1].
    Devuelve array del mismo shape, también en [0, 1].
    """
    g = gamma_from_strength(params.strength)
    x = np.clip(x, 0.0, 1.0)
    return np.power(x, g)


def build_lut(params: ToneParams) -> np.ndarray:
    """
    LUT uint8 de 256 entradas. Aplicable con cv2.LUT sobre canales uint8.
    """
    x = np.arange(256, dtype=np.float32) / 255.0
    y = tone_map(x, params)
    return np.clip(np.round(y * 255.0), 0, 255).astype(np.uint8)
