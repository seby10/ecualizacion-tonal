"""
Entrada/salida de imágenes JPG/PNG.
Internamente trabajamos en RGB (no BGR de OpenCV) para coherencia con Qt/matplotlib.
"""
from pathlib import Path
import cv2
import numpy as np


SUPPORTED_EXT = {".jpg", ".jpeg", ".png"}


def load_image(path: str | Path) -> np.ndarray:
    """
    Carga una imagen desde disco y la devuelve en formato RGB uint8.
    Lanza ValueError si el formato no es soportado o la lectura falla.
    """
    path = Path(path)
    if path.suffix.lower() not in SUPPORTED_EXT:
        raise ValueError(f"Formato no soportado: {path.suffix}")
    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"No se pudo leer la imagen: {path}")
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def save_image(path: str | Path, rgb: np.ndarray) -> None:
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    ok = cv2.imwrite(str(path), bgr)
    if not ok:
        raise IOError(f"No se pudo escribir: {path}")
