"""
Curva tonal por canal — modelo simplificado.

Una sola técnica: contrast stretching (Gonzalez & Woods §3.2).
Cada canal se describe por una ventana [min_in, max_in] que se estira
linealmente hasta cubrir [0, 255].

La construcción real de la LUT vive en `core.redistribution` (manual).
"""
from __future__ import annotations
from dataclasses import dataclass

import numpy as np

from core import redistribution as redist


@dataclass
class ChannelCurve:
    min_in: int = 0
    max_in: int = 255


def build_lut(curve: ChannelCurve) -> np.ndarray:
    """LUT uint8 de 256 entradas para la ventana [min_in, max_in]."""
    return redist.lut_stretch(curve.min_in, curve.max_in)
