"""
Ventana principal.

Layout (de arriba hacia abajo):
  0) Toolbar: Abrir / Guardar / Reset todo.
  1) Imagen original (centrada, ocupa las 3 columnas).
  2) Tres imágenes: canal R, G, B (modificados, pseudo-coloreados).
  3) Tres histogramas, uno por canal (del canal modificado).
  4) Tres sliders, uno por canal.
  5) Tres imágenes: modificada (RGB), binarizada (Otsu), thumbnail.

Al mover un slider se recalcula la curva, la LUT, el canal modificado,
su histograma y la imagen final. Un pequeño debounce evita recomputar
en cada micro-movimiento.
"""
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QGridLayout, QFileDialog, QToolBar,
    QMessageBox, QStatusBar, QScrollArea,
)

from core.image_io import load_image, save_image
from core.histogram import histogram_uint8
from core.pipeline import process, ProcessResult
from core.tone_curve import ToneParams, build_lut

from gui.image_viewer import ImagePanel
from gui.histogram_widget import HistogramWidget
from gui.channel_panel import ChannelSlider


CHANNEL_COLORS = ("red", "green", "blue")
CHANNEL_NAMES = ("R", "G", "B")


class MainWindow(QMainWindow):
    DEBOUNCE_MS = 60

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ecualización Tonal por Canales")
        self.resize(1280, 1000)

        self._original: np.ndarray | None = None

        self._build_ui()
        self._build_toolbar()

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(self.DEBOUNCE_MS)
        self._preview_timer.timeout.connect(self._recompute)

        for s in self._sliders:
            s.valueChanged.connect(lambda _=None: self._preview_timer.start())

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Abre una imagen para comenzar.")

    # ---------- construcción UI ----------
    def _build_ui(self) -> None:
        central = QWidget()
        grid = QGridLayout(central)
        grid.setContentsMargins(6, 6, 6, 6)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)

        # fila 0: imagen original (3 columnas)
        self.panel_original = ImagePanel("Imagen original", min_size=(420, 260))
        grid.addWidget(self.panel_original, 0, 0, 1, 3)

        # fila 1: canales R, G, B (modificados)
        self._channel_panels: list[ImagePanel] = []
        for i, (name, color) in enumerate(zip(CHANNEL_NAMES, CHANNEL_COLORS)):
            panel = ImagePanel(f"Canal {name}", min_size=(180, 180))
            self._channel_panels.append(panel)
            grid.addWidget(panel, 1, i)

        # fila 2: histogramas
        self._histograms: list[HistogramWidget] = []
        for i, color in enumerate(CHANNEL_COLORS):
            hw = HistogramWidget(color=color)
            self._histograms.append(hw)
            grid.addWidget(hw, 2, i)

        # fila 3: sliders
        self._sliders: list[ChannelSlider] = []
        for i, (name, color) in enumerate(zip(CHANNEL_NAMES, CHANNEL_COLORS)):
            s = ChannelSlider(name, color)
            self._sliders.append(s)
            grid.addWidget(s, 3, i)

        # fila 4: resultados finales
        self.panel_modified = ImagePanel("Modificada", min_size=(180, 180))
        self.panel_binary   = ImagePanel("Binarizada (Otsu)", min_size=(180, 180))
        self.panel_thumb    = ImagePanel("Thumbnail", min_size=(180, 180))
        grid.addWidget(self.panel_modified, 4, 0)
        grid.addWidget(self.panel_binary,   4, 1)
        grid.addWidget(self.panel_thumb,    4, 2)

        # proporciones verticales: los histogramas ahora pesan fuerte
        grid.setRowStretch(0, 3)   # original
        grid.setRowStretch(1, 2)   # canales
        grid.setRowStretch(2, 3)   # histogramas (legibles)
        grid.setRowStretch(3, 0)   # sliders (altura fija)
        grid.setRowStretch(4, 2)   # resultados
        for c in range(3):
            grid.setColumnStretch(c, 1)

        # altura mínima para garantizar lectura: si la ventana es más baja,
        # aparece scroll vertical.
        central.setMinimumHeight(1400)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(central)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setCentralWidget(scroll)

    def _build_toolbar(self) -> None:
        tb = QToolBar("Principal")
        tb.setMovable(False)
        self.addToolBar(tb)

        act_open = QAction("Abrir", self)
        act_open.triggered.connect(self._on_open)
        tb.addAction(act_open)

        act_save = QAction("Guardar modificada", self)
        act_save.triggered.connect(self._on_save)
        tb.addAction(act_save)

        tb.addSeparator()

        act_reset = QAction("Reset todo", self)
        act_reset.triggered.connect(self._on_reset_all)
        tb.addAction(act_reset)

    # ---------- eventos ----------
    def _on_open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir imagen", "",
            "Imágenes (*.jpg *.jpeg *.png)",
        )
        if not path:
            return
        try:
            img = load_image(path)
        except Exception as e:
            QMessageBox.critical(self, "Error al cargar", str(e))
            return
        self._original = img
        self.panel_original.set_image(img)
        self._recompute()
        self.statusBar().showMessage(
            f"Cargada: {Path(path).name}   {img.shape[1]}×{img.shape[0]}"
        )

    def _on_save(self) -> None:
        if self._original is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar imagen modificada", "",
            "PNG (*.png);;JPEG (*.jpg *.jpeg)",
        )
        if not path:
            return
        result = self._compute()
        try:
            save_image(path, result.modified)
            self.statusBar().showMessage(f"Guardado: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", str(e))

    def _on_reset_all(self) -> None:
        for s in self._sliders:
            s.reset()

    # ---------- cómputo ----------
    def _current_params(self) -> tuple[ToneParams, ToneParams, ToneParams]:
        return tuple(ToneParams(strength=s.value()) for s in self._sliders)  # type: ignore[return-value]

    def _compute(self) -> ProcessResult:
        assert self._original is not None
        r, g, b = self._current_params()
        return process(self._original, r, g, b)

    def _recompute(self) -> None:
        params = self._current_params()

        # LUTs siempre, aunque no haya imagen todavía
        luts = [build_lut(p) for p in params]

        if self._original is None:
            # muestra solo la curva teórica sobre un histograma vacío
            for hw, lut in zip(self._histograms, luts):
                hw.set_histogram(np.zeros(256, dtype=np.int64))
                hw.set_lut(lut)
            return

        result = self._compute()

        # canales pseudo-coloreados
        for panel, colored in zip(self._channel_panels, result.channels_colored):
            panel.set_image(colored)

        # histogramas del canal MODIFICADO + curva LUT superpuesta
        for hw, ch, lut in zip(self._histograms, result.channels_modified, luts):
            hw.set_histogram(histogram_uint8(ch))
            hw.set_lut(lut)

        # resultados finales
        self.panel_modified.set_image(result.modified)
        self.panel_binary.set_image(result.binary)
        self.panel_thumb.set_image(result.thumbnail)
