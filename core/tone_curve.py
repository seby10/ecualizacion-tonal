"""
Curva tonal por canal — modelo simplificado.

Una sola técnica: ecualización de histograma (Gonzalez & Woods §3.3).
La curva se construye a partir de la CDF del canal y se mezcla con la
identidad mediante `strength` ∈ [0, 1]:
    strength = 0  → identidad (sin cambios)
    strength = 1  → ecualización completa
    intermedio    → blend lineal entre ambas

Sin clipping: la operación es monótona y NO tira información — solo
redistribuye intensidades para aplanar el histograma.

La construcción real de la LUT vive en `core.redistribution.lut_equalize`.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

import numpy as np

from core import redistribution as redist


@dataclass
class ChannelCurve:
    strength: float = 1.0   # ∈ [0, 1]


def build_lut(curve: ChannelCurve, channel: Optional[np.ndarray] = None) -> np.ndarray:
    """LUT uint8 de 256 entradas. Requiere el canal (la curva depende del histograma)."""
    if channel is None:
        return np.arange(256, dtype=np.uint8)
    return redist.lut_equalize(channel, curve.strength)
