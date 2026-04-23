"""
Widget matplotlib embebido en Qt: histograma de 256 bins con la curva tonal
superpuesta (eje Y derecho escalado a [0, 255]).
"""
import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas


class HistogramWidget(QWidget):
    MIN_HEIGHT = 260   # px; garantiza legibilidad incluso en ventanas chicas

    def __init__(self, color: str = "gray", parent=None):
        super().__init__(parent)
        self.color = color

        self.figure = Figure(figsize=(5.5, 3.2), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumHeight(self.MIN_HEIGHT)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding,
                                  QSizePolicy.Policy.Expanding)

        self.ax = self.figure.add_subplot(111)
        self.ax2 = self.ax.twinx()   # eje derecho para la curva LUT [0, 255]
        self._configure_axes()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        self.setMinimumHeight(self.MIN_HEIGHT)

        self._hist = np.zeros(256, dtype=np.int64)
        self._lut: np.ndarray | None = None

    def _configure_axes(self) -> None:
        self.ax.set_xlim(0, 255)
        self.ax.set_xticks([0, 32, 64, 96, 128, 160, 192, 224, 255])
        self.ax.set_xlabel("Intensidad (0–255)", fontsize=10)
        self.ax.set_ylabel("Nº de píxeles", fontsize=10)
        self.ax.tick_params(axis="both", labelsize=9)
        self.ax.grid(True, alpha=0.25)

        self.ax2.set_ylim(0, 255)
        self.ax2.set_ylabel("Salida de la curva", fontsize=10, color="black")
        self.ax2.tick_params(axis="y", labelsize=9)

    def set_histogram(self, hist: np.ndarray) -> None:
        self._hist = hist
        self._redraw()

    def set_lut(self, lut: np.ndarray | None) -> None:
        self._lut = lut
        self._redraw()

    def _redraw(self) -> None:
        self.ax.clear()
        self.ax2.clear()
        self._configure_axes()

        x = np.arange(256)
        self.ax.fill_between(x, self._hist, step="mid",
                             color=self.color, alpha=0.55,
                             edgecolor=self.color, linewidth=0.6)

        if self._lut is not None:
            self.ax2.plot(x, self._lut, color="black", linewidth=1.6,
                          label="Curva tonal")
            # diagonal identidad de referencia
            self.ax2.plot([0, 255], [0, 255], color="gray",
                          linestyle="--", linewidth=0.9, alpha=0.6)

        self.canvas.draw_idle()
