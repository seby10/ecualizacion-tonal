"""
Curva tonal por canal — remapeo de rango (redistribución sin pérdida).

El usuario define:
    from_min, from_max  →  rango de entrada a redistribuir
    to_min,   to_max    →  rango destino donde se colocan esos píxeles

La LUT resultante:
    x en [from_min, from_max]  →  interpolación lineal a [to_min, to_max]
    x fuera de ese rango       →  identidad (lut[x] = x)

NO se pierde ningún píxel: todos se conservan, solo cambian de posición
en el histograma. Esto es lo que el profesor llama "redistribución tonal
con interpolación".

La construcción real de la LUT vive en `core.redistribution.lut_remap`.
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from core import redistribution as redist


@dataclass
class ChannelCurve:
    from_min: int = 0    # inicio del rango de entrada
    from_max: int = 255  # fin del rango de entrada
    to_min:   int = 0    # inicio del rango destino
    to_max:   int = 255  # fin del rango destino
    transfer_ratio: float = 1.0  # 0.0 a 1.0, porcentaje de píxeles a mover


def build_lut(curve: ChannelCurve, channel: np.ndarray | None = None) -> np.ndarray:
    """LUT uint8 de 256 entradas usando remapeo lineal de rango."""
    return redist.lut_remap(curve.from_min, curve.from_max,
                            curve.to_min,   curve.to_max)