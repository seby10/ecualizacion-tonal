"""
Pipeline de procesamiento.

Orden de procesamiento (importante didácticamente):
    original
        → aplicar LUT por canal           (apply_channel_curves)
        → recomponer imagen modificada    (np.stack)
        → reducir a thumbnail pixelado    (pixelated_thumbnail)
        → binarizar el thumbnail          (binarize_manual)

La binarización SIEMPRE se calcula sobre el thumbnail. Por tanto:
  * cambiar la pixelación   → cambia thumbnail Y binarizada.
  * cambiar el umbral       → cambia solo la binarizada.

Operaciones de redistribución (LUT) y binarización están implementadas
manualmente; ver core.redistribution.
"""
from dataclasses import dataclass
import cv2
import numpy as np

from core.tone_curve import ChannelCurve, build_lut


@dataclass
class OutputParams:
    pixelation: int = 4                  # factor de downsample del thumbnail (1..32)
    binary_threshold: int | None = None  # None = Otsu manual; entero = umbral fijo
    thumb_display_side: int = 220        # tamaño objetivo de visualización
    min_contour_area: int = 50           # área mínima para filtrar contornos (px²)


@dataclass
class ProcessResult:
    channels_modified: tuple[np.ndarray, np.ndarray, np.ndarray]
    modified:  np.ndarray
    thumbnail: np.ndarray  # pixelado, RGB uint8
    binary:    np.ndarray  # binarización del THUMBNAIL (mismo tamaño que thumb)
    otsu_value: int
    contours_image: np.ndarray  # thumbnail con contornos y bounding boxes
    contour_count: int          # número de objetos detectados


# =====================================================================
# Aplicación de la LUT a un canal:  out[y,x] = lut[ in[y,x] ]
# =====================================================================
# Reemplaza cv2.LUT — el indexado avanzado de NumPy es la operación
# fundamental (no hay redistribución oculta).

def apply_lut(channel: np.ndarray, lut: np.ndarray) -> np.ndarray:
    return lut[channel]


# =====================================================================
# Aplicar las tres curvas y devolver canales separados
# =====================================================================
def apply_channel_curves(
    rgb: np.ndarray,
    r: ChannelCurve, g: ChannelCurve, b: ChannelCurve,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    lut_r = build_lut(r, rgb[..., 0])
    lut_g = build_lut(g, rgb[..., 1])
    lut_b = build_lut(b, rgb[..., 2])
    ch_r = apply_lut(rgb[..., 0], lut_r)
    ch_g = apply_lut(rgb[..., 1], lut_g)
    ch_b = apply_lut(rgb[..., 2], lut_b)
    return ch_r, ch_g, ch_b


# =====================================================================
# Conversión a luminancia BT.601 (sin cv2.cvtColor) — manual
# =====================================================================
def to_grayscale_bt601(rgb: np.ndarray) -> np.ndarray:
    r = rgb[..., 0].astype(np.float32)
    g = rgb[..., 1].astype(np.float32)
    b = rgb[..., 2].astype(np.float32)
    y = 0.299 * r + 0.587 * g + 0.114 * b
    return np.clip(np.round(y), 0, 255).astype(np.uint8)


# =====================================================================
# Binarización manual:
#   automática (Otsu)  ó  manual con umbral fijo.
# =====================================================================
def _otsu_threshold(gray: np.ndarray) -> int:
    """
    Implementación manual del algoritmo de Otsu:
    busca el umbral t ∈ [0, 255] que minimiza la varianza intra-clase
    (equivalente a maximizar la varianza inter-clase).
    """
    hist = np.bincount(gray.ravel(), minlength=256).astype(np.float64)
    total = float(gray.size)
    if total <= 0:
        return 128

    sum_total = float(np.dot(np.arange(256), hist))

    sum_b = 0.0    # suma ponderada de la clase "fondo"
    w_b = 0.0      # peso de la clase "fondo"
    var_max = -1.0
    threshold = 0

    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_total - sum_b) / w_f
        var_between = w_b * w_f * (m_b - m_f) ** 2
        if var_between > var_max:
            var_max = var_between
            threshold = t
    return int(threshold)


def binarize_manual(rgb: np.ndarray, threshold: int | None) -> tuple[np.ndarray, int]:
    """
    Binariza una imagen RGB usando luminancia BT.601 + umbral.
    Si threshold es None se usa Otsu (manual).
    """
    gray = to_grayscale_bt601(rgb)
    t = _otsu_threshold(gray) if threshold is None else int(np.clip(threshold, 0, 255))
    binary = np.where(gray >= t, np.uint8(255), np.uint8(0))
    return binary, t


# =====================================================================
# Thumbnail pixelado (downsample por bloques + upsample nearest)
# =====================================================================
def pixelated_thumbnail(rgb: np.ndarray, factor: int, display_side: int) -> np.ndarray:
    factor = max(1, int(factor))
    h, w = rgb.shape[:2]

    down_w = max(1, w // factor)
    down_h = max(1, h // factor)
    small = cv2.resize(rgb, (down_w, down_h), interpolation=cv2.INTER_AREA)

    scale = display_side / max(small.shape[:2])
    disp_w = max(1, int(round(small.shape[1] * scale)))
    disp_h = max(1, int(round(small.shape[0] * scale)))
    return cv2.resize(small, (disp_w, disp_h), interpolation=cv2.INTER_NEAREST)


# =====================================================================
# Detección de contornos (paso de visión por computadora)
# =====================================================================
#
# Este paso CONSUME la salida del preprocesamiento (imagen binarizada)
# y demuestra que la binarización separa correctamente objeto/fondo.
#
# Operaciones:
#   1. cv2.findContours sobre la imagen binaria (border following).
#   2. Filtrado por área mínima para eliminar ruido.
#   3. Dibujo de contornos (verde) y bounding boxes (rojo) sobre
#      una copia del thumbnail a color.
#   4. Etiquetas numéricas para cada objeto detectado.
#
# NOTA: aquí SÍ se usa cv2.findContours porque la detección de
# contornos es el paso de VISIÓN POR COMPUTADORA, no de
# preprocesamiento. El preprocesamiento (ecualización, binarización,
# Otsu) fue implementado manualmente.
# =====================================================================

def detect_contours(
    binary: np.ndarray,
    color_bg: np.ndarray,
    min_area: int = 50,
) -> tuple[np.ndarray, int]:
    """
    Detecta contornos en la imagen binarizada y los dibuja sobre
    una copia de la imagen a color (thumbnail).

    Parámetros:
        binary   : imagen binaria uint8 (0 ó 255).
        color_bg : imagen RGB uint8 del mismo tamaño (thumbnail).
        min_area : área mínima en píxeles² para considerar un contorno.

    Retorna:
        (imagen_con_contornos, número_de_objetos)
    """
    # findContours espera fondo=0, objeto=255
    contours, _ = cv2.findContours(
        binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE,
    )

    # Filtrar por área mínima → elimina ruido y artefactos pequeños
    filtered = [c for c in contours if cv2.contourArea(c) >= min_area]

    # Dibujar sobre copia de la imagen a color
    canvas = color_bg.copy()

    # Contornos en verde (grosor 2)
    cv2.drawContours(canvas, filtered, -1, (0, 255, 0), 2)

    # Bounding boxes en rojo + etiqueta numérica en amarillo
    for i, c in enumerate(filtered):
        x, y, w, h = cv2.boundingRect(c)
        cv2.rectangle(canvas, (x, y), (x + w, y + h), (255, 50, 50), 1)
        label_y = max(y - 4, 12)
        cv2.putText(
            canvas, str(i + 1),
            (x + 2, label_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 0), 1,
            cv2.LINE_AA,
        )

    return canvas, len(filtered)


# =====================================================================
# Pipeline completo
# =====================================================================
def process(
    rgb: np.ndarray,
    r: ChannelCurve, g: ChannelCurve, b: ChannelCurve,
    outputs: OutputParams,
) -> ProcessResult:
    # 1) aplicar curvas tonales por canal (LUT manual)
    ch_r, ch_g, ch_b = apply_channel_curves(rgb, r, g, b)

    # 2) recomponer la imagen modificada
    modified = np.stack([ch_r, ch_g, ch_b], axis=-1)

    # 3) thumbnail pixelado a partir de la modificada
    thumb = pixelated_thumbnail(modified, outputs.pixelation, outputs.thumb_display_side)

    # 4) binarizar el thumbnail (la binarización HEREDA de la pixelación)
    binary, otsu_value = binarize_manual(thumb, outputs.binary_threshold)

    # 5) detección de contornos sobre la binarizada → visión por computadora
    contours_img, contour_count = detect_contours(
        binary, thumb, outputs.min_contour_area,
    )

    return ProcessResult(
        channels_modified=(ch_r, ch_g, ch_b),
        modified=modified,
        thumbnail=thumb,
        binary=binary,
        otsu_value=otsu_value,
        contours_image=contours_img,
        contour_count=contour_count,
    )
