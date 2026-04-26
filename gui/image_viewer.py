"""
Panel individual que muestra una imagen escalada con un título.
Se usa para cada una de las vistas (original, canal R, G, B, modificada, ...).
"""
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel

from utils.qimage_bridge import ndarray_to_qpixmap


class ImagePanel(QFrame):
    def __init__(self, title: str, min_size: tuple[int, int] = (200, 200), parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._title = QLabel(title)
        font = self._title.font()
        font.setBold(True)
        self._title.setFont(font)
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._img = QLabel("(sin imagen)")
        self._img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img.setMinimumSize(*min_size)
        self._img.setStyleSheet("background: #222; color: #888;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self._title)
        layout.addWidget(self._img, 1)

        self._pixmap = None

    def set_title(self, title: str) -> None:
        self._title.setText(title)

    def set_image(self, arr: np.ndarray | None) -> None:
        if arr is None:
            self._pixmap = None
            self._img.setText("(sin imagen)")
            return
        self._pixmap = ndarray_to_qpixmap(arr)
        self._update_scaled()

    def _update_scaled(self) -> None:
        if self._pixmap is None:
            return
        self._img.setPixmap(self._pixmap.scaled(
            self._img.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_scaled()
