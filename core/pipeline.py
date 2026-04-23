"""
Orquestador del flujo de procesamiento.

Entrega:
  * canales_modificados: R', G', B' (arrays 2D uint8)
  * canales_coloreados:  cada canal reintegrado en su color (RGB con ceros
                         en los otros canales) para visualización didáctica.
  * modified:            imagen RGB uint8 recompuesta.
  * binary:              imagen binarizada por Otsu sobre la luminancia.
  * thumbnail:           imagen reducida (máx. lado configurable).
"""
from dataclasses import dataclass
import cv2
import numpy as np

from core.tone_curve import ToneParams, build_lut


@dataclass
class ProcessResult:
    channels_modified: tuple[np.ndarray, np.ndarray, np.ndarray]
    channels_colored:  tuple[np.ndarray, np.ndarray, np.ndarray]
    modified:  np.ndarray
    binary:    np.ndarray
    thumbnail: np.ndarray


def channel_as_colored(channel: np.ndarray, idx: int) -> np.ndarray:
    """
    Devuelve una imagen RGB del mismo tamaño con el canal `idx` ocupado
    por `channel` y los otros dos canales en cero. Útil para visualizar
    "el canal R en rojo", "el canal G en verde", etc.
    """
    h, w = channel.shape[:2]
    out = np.zeros((h, w, 3), dtype=np.uint8)
    out[..., idx] = channel
    return out


def apply_channel_curves(
    rgb: np.ndarray,
    r: ToneParams, g: ToneParams, b: ToneParams,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Aplica la LUT correspondiente a cada canal y devuelve los tres canales
    modificados (arrays 2D uint8). La recomposición queda a cargo del llamador.
    """
    lut_r = build_lut(r)
    lut_g = build_lut(g)
    lut_b = build_lut(b)
    ch_r = cv2.LUT(rgb[..., 0], lut_r)
    ch_g = cv2.LUT(rgb[..., 1], lut_g)
    ch_b = cv2.LUT(rgb[..., 2], lut_b)
    return ch_r, ch_g, ch_b


def binarize_otsu(rgb: np.ndarray) -> np.ndarray:
    """Binarización Otsu sobre la luminancia (BT.601 aprox vía cvtColor)."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    _, binary = cv2.threshold(gray, 0, 255,
                              cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def make_thumbnail(rgb: np.ndarray, max_side: int = 160) -> np.ndarray:
    h, w = rgb.shape[:2]
    scale = max_side / max(h, w)
    if scale >= 1.0:
        return rgb.copy()
    nh, nw = max(1, int(h * scale)), max(1, int(w * scale))
    return cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_AREA)


def process(
    rgb: np.ndarray,
    r: ToneParams, g: ToneParams, b: ToneParams,
    thumb_side: int = 160,
) -> ProcessResult:
    ch_r, ch_g, ch_b = apply_channel_curves(rgb, r, g, b)

    modified = np.stack([ch_r, ch_g, ch_b], axis=-1)

    colored = (
        channel_as_colored(ch_r, 0),
        channel_as_colored(ch_g, 1),
        channel_as_colored(ch_b, 2),
    )

    binary = binarize_otsu(modified)
    thumb = make_thumbnail(modified, max_side=thumb_side)

    return ProcessResult(
        channels_modified=(ch_r, ch_g, ch_b),
        channels_colored=colored,
        modified=modified,
        binary=binary,
        thumbnail=thumb,
    )
