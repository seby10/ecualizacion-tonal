"""
Curva tonal por canal (Contrast Stretching).
max_in = 255 → identidad
max_in < 255 → estiramiento
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
