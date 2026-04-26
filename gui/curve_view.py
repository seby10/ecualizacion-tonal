"""
Widget matplotlib embebido que muestra:
  * Histograma del canal (relleno en el color del canal).
  * Curva tonal actual (línea negra, eje Y derecho en [0, 255]).
    En modo ecualización, la curva es la CDF normalizada del canal mezclada
    con la identidad según `strength`.
  * Diagonal identidad de referencia (gris punteada).
"""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavToolbar


class _FigureCanvasNoWheel(FigureCanvas):
    """Wheel sin Ctrl: scroll de página. Ctrl+wheel: zoom del canvas."""

    def wheelEvent(self, event):  # noqa: N802
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            super().wheelEvent(event)
            return
        event.ignore()


class CurveView(QWidget):
    MIN_HEIGHT = 275

    def __init__(self, color: str = "gray", parent=None):
        super().__init__(parent)
        self.color = color

        self._hist = np.zeros(256, dtype=np.int64)
        self._lut: np.ndarray | None = None

        self.figure = Figure(figsize=(5.8, 3.3), tight_layout=True)
        self.canvas = _FigureCanvasNoWheel(self.figure)
        self.canvas.setMinimumHeight(self.MIN_HEIGHT)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding,
                                  QSizePolicy.Policy.Expanding)

        self.toolbar = NavToolbar(self.canvas, self)
        self.toolbar.setIconSize(self.toolbar.iconSize() * 0.75)

        self.ax = self.figure.add_subplot(111)
        self.ax2 = self.ax.twinx()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        self.setMinimumHeight(self.MIN_HEIGHT + 30)
        self._configure_axes()
        self._redraw()

    def set_histogram(self, hist: np.ndarray) -> None:
        self._hist = hist
        self._redraw()

    def set_lut(self, lut: np.ndarray | None) -> None:
        self._lut = lut
        self._redraw()

    # ------------- dibujo -------------
    def _configure_axes(self) -> None:
        self.ax.set_xlim(0, 255)
        self.ax.set_xticks([0, 32, 64, 96, 128, 160, 192, 224, 255])
        self.ax.set_xlabel("Intensidad (0–255)", fontsize=10)
        self.ax.set_ylabel("Nº de píxeles", fontsize=10)
        self.ax.tick_params(axis="both", labelsize=9)
        self.ax.grid(True, alpha=0.25)

        self.ax2.set_ylim(0, 255)
        self.ax2.tick_params(axis="y", labelsize=9)

    def _redraw(self) -> None:
        self.ax.clear()
        self.ax2.clear()
        self._configure_axes()

        x = np.arange(256)

        # histograma
        if self._hist.max() > 0:
            self.ax.fill_between(x, self._hist, step="mid",
                                 color=self.color, alpha=0.55,
                                 edgecolor=self.color, linewidth=0.6)

        # diagonal identidad
        self.ax2.plot([0, 255], [0, 255], color="gray",
                      linestyle="--", linewidth=0.9, alpha=0.55)

        # curva tonal (CDF blendeada con identidad)
        if self._lut is not None:
            self.ax2.plot(x, self._lut, color="black", linewidth=1.8)

        self.canvas.draw_idle()
