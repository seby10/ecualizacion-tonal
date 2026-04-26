"""
Widget matplotlib embebido con DOS subgráficas por canal:

  [izq]  Histograma ORIGINAL
           — muestra la distribución de píxeles del canal sin tocar
           — sombreado naranja sobre [from_min, from_max]: zona que se va a mover
  [der]  Histograma MODIFICADO
           — muestra la distribución DESPUÉS de aplicar la LUT
           — sombreado azul sobre [to_min, to_max]: zona donde llegaron los píxeles

Separar los histogramas es clave didácticamente: el alumno ve
exactamente de dónde salieron los píxeles y a dónde llegaron.
"""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy

from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.patches import Patch


# ── paleta de colores profesional ────────────────────────────────────
_BG       = "#1e1e2e"   # fondo oscuro
_FG       = "#cdd6f4"   # texto claro
_GRID     = "#45475a"   # líneas de cuadrícula
_ORANGE   = "#fab387"   # zona de origen (más suave que el naranja puro)
_BLUE     = "#89b4fa"   # zona destino
_ACCENT   = {
    "red":   "#f38ba8",
    "green": "#a6e3a1",
    "blue":  "#89b4fa",
}


class _Canvas(FigureCanvas):
    """Canvas que solo hace zoom con Ctrl+rueda (no intercepta scroll normal)."""
    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            super().wheelEvent(event)
        else:
            event.ignore()


class CurveView(QWidget):
    """Doble histograma (original vs. modificado) para un canal."""
    MIN_HEIGHT = 220

    def __init__(self, color: str = "gray", parent=None):
        super().__init__(parent)
        self.color = color
        self._bar_color = _ACCENT.get(color, "#b4befe")

        self._hist_orig: np.ndarray = np.zeros(256, dtype=np.int64)
        self._hist_mod:  np.ndarray = np.zeros(256, dtype=np.int64)
        self._from_min: int = 0
        self._from_max: int = 255
        self._to_min:   int = 0
        self._to_max:   int = 255

        # figura con 2 subplots — fondo oscuro
        self.figure = Figure(figsize=(8, 2.6), facecolor=_BG)
        self.figure.subplots_adjust(left=0.06, right=0.97, top=0.86,
                                     bottom=0.18, wspace=0.28)
        self.canvas = _Canvas(self.figure)
        self.canvas.setMinimumHeight(self.MIN_HEIGHT)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding,
                                  QSizePolicy.Policy.Expanding)

        self.ax_orig, self.ax_mod = self.figure.subplots(1, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        self.setMinimumHeight(self.MIN_HEIGHT)

        self._configure_axes()
        self._redraw()

    # ---------- API pública ----------

    def set_histogram_orig(self, hist: np.ndarray) -> None:
        self._hist_orig = hist
        self._redraw()

    def set_histogram_mod(self, hist: np.ndarray) -> None:
        self._hist_mod = hist
        self._redraw()

    def set_lut(self, lut: np.ndarray | None) -> None:
        # Ya no dibujamos LUT, pero mantenemos la interfaz para no romper
        pass

    def set_window(self, from_min: int, from_max: int,
                   to_min: int, to_max: int) -> None:
        self._from_min = int(from_min)
        self._from_max = int(from_max)
        self._to_min   = int(to_min)
        self._to_max   = int(to_max)
        self._redraw()

    # ---------- dibujo ----------

    def _style_ax(self, ax) -> None:
        """Aplica el tema oscuro y legible a un eje."""
        ax.set_facecolor(_BG)
        ax.set_xlim(0, 255)
        ax.set_xticks([0, 32, 64, 96, 128, 160, 192, 224, 255])
        ax.set_xticklabels(
            ["0", "", "64", "", "128", "", "192", "", "255"],
            fontsize=8, color=_FG,
        )
        ax.tick_params(axis="y", labelsize=7, colors=_FG)
        ax.tick_params(axis="x", colors=_FG)
        ax.set_xlabel("Intensidad (0–255)", fontsize=9, color=_FG,
                       labelpad=4)
        ax.set_ylabel("Nº de píxeles", fontsize=9, color=_FG, labelpad=4)
        ax.grid(True, color=_GRID, alpha=0.35, linewidth=0.5)
        for spine in ax.spines.values():
            spine.set_color(_GRID)

    def _configure_axes(self) -> None:
        for ax in (self.ax_orig, self.ax_mod):
            self._style_ax(ax)

    def _redraw(self) -> None:
        for ax in (self.ax_orig, self.ax_mod):
            ax.clear()
        self._configure_axes()

        x = np.arange(256)
        bar_color = self._bar_color

        # ── Histograma ORIGINAL ──────────────────────────────────────
        self.ax_orig.set_title(
            "Histograma ORIGINAL", fontsize=10, fontweight="bold",
            color=_FG, pad=6,
        )

        if self._hist_orig.max() > 0:
            self.ax_orig.bar(
                x, self._hist_orig, width=1.0,
                color=bar_color, alpha=0.55, edgecolor="none",
            )
            # escala Y automática con un poco de margen
            ymax = float(self._hist_orig.max()) * 1.1
            self.ax_orig.set_ylim(0, ymax)

        # sombreado naranja = zona que se va a mover
        if self._from_max > self._from_min and self._hist_orig.max() > 0:
            self.ax_orig.axvspan(
                self._from_min, self._from_max,
                color=_ORANGE, alpha=0.22,
            )
            self.ax_orig.axvline(self._from_min, color=_ORANGE,
                                 linewidth=1.6, linestyle="--", alpha=0.9)
            self.ax_orig.axvline(self._from_max, color=_ORANGE,
                                 linewidth=1.6, linestyle="--", alpha=0.9)
            self.ax_orig.legend(
                handles=[Patch(color=_ORANGE, alpha=0.55,
                               label=f"Origen [{self._from_min} – {self._from_max}]")],
                fontsize=8, loc="upper right", framealpha=0.85,
                facecolor="#313244", edgecolor=_GRID, labelcolor=_FG,
            )

        # ── Histograma MODIFICADO ────────────────────────────────────
        self.ax_mod.set_title(
            "Histograma MODIFICADO", fontsize=10, fontweight="bold",
            color=_FG, pad=6,
        )

        if self._hist_mod.max() > 0:
            self.ax_mod.bar(
                x, self._hist_mod, width=1.0,
                color=_BLUE, alpha=0.55, edgecolor="none",
            )
            ymax = float(self._hist_mod.max()) * 1.1
            self.ax_mod.set_ylim(0, ymax)

        # sombreado azul = zona donde llegaron los píxeles
        if self._to_max > self._to_min and self._hist_mod.max() > 0:
            self.ax_mod.axvspan(
                self._to_min, self._to_max,
                color=_BLUE, alpha=0.15,
            )
            self.ax_mod.axvline(self._to_min, color=_BLUE,
                                linewidth=1.6, linestyle="--", alpha=0.9)
            self.ax_mod.axvline(self._to_max, color=_BLUE,
                                linewidth=1.6, linestyle="--", alpha=0.9)
            self.ax_mod.legend(
                handles=[Patch(color=_BLUE, alpha=0.55,
                               label=f"Destino [{self._to_min} – {self._to_max}]")],
                fontsize=8, loc="upper right", framealpha=0.85,
                facecolor="#313244", edgecolor=_GRID, labelcolor=_FG,
            )

        self.canvas.draw_idle()