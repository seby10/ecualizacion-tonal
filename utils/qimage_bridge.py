"""
Conversión entre ndarray de NumPy y QImage/QPixmap de Qt.
"""
import numpy as np
from PySide6.QtGui import QImage, QPixmap


def ndarray_to_qpixmap(arr: np.ndarray) -> QPixmap:
    """
    Convierte un ndarray a QPixmap.
    Soporta 2D (gris) y 3D RGB, todos uint8.
    """
    if arr.dtype != np.uint8:
        arr = np.clip(arr, 0, 255).astype(np.uint8)

    arr = np.ascontiguousarray(arr)

    if arr.ndim == 2:
        h, w = arr.shape
        qimg = QImage(arr.data, w, h, w, QImage.Format.Format_Grayscale8)
    elif arr.ndim == 3 and arr.shape[2] == 3:
        h, w, _ = arr.shape
        qimg = QImage(arr.data, w, h, 3 * w, QImage.Format.Format_RGB888)
    else:
        raise ValueError(f"Shape no soportado: {arr.shape}")

    # copy() desancla los datos del ndarray (que puede ser reciclado)
    return QPixmap.fromImage(qimg.copy())
