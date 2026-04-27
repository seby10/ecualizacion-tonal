"""
Curva tonal por canal — modelo simplificado.

Una sola técnica: contrast stretching lineal con min fijo en 0.
La curva se construye estirando el rango [0, max_in] hasta [0, 255]:
    max_in = 255  → identidad (sin cambios)
    max_in < 255  → estiramiento (ilumina la imagen)

Sin clipping: la operación es monótona y NO tira información — solo
redistribuye intensidades para aplanar el histograma.

La construcción real de la LUT vive en `core.redistribution.lut_stretch`.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

import numpy as np

from core import redistribution as redist


@dataclass
class ChannelCurve:
    max_in: int = 255   # ∈ [1, 255]


def build_lut(curve: ChannelCurve, channel: Optional[np.ndarray] = None) -> np.ndarray:
    """LUT uint8 de 256 entradas. Con min=0 y max=curve.max_in."""
    return redist.lut_stretch(0, curve.max_in)
