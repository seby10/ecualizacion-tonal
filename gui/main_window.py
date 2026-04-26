"""
Ventana principal — modelo simplificado.

Una sola técnica de redistribución por canal: ecualización de histograma
(Gonzalez & Woods §3.3). Cada canal expone un slider strength ∈ [0, 1]:
    0 = identidad (sin cambios)
    1 = ecualización completa
    intermedio = blend lineal con la identidad

Sin clipping: la operación es monótona y NO tira información — solo
redistribuye intensidades para aplanar el histograma. Útil como
preprocesamiento previo a la binarización (separa mejor objeto/fondo).

Pipeline: original → curvas → modificada → thumbnail (pixelado) → binarizada.
La binarizada SIEMPRE se calcula sobre el thumbnail.

Las imágenes de canal se muestran en escala de grises (matrices 2D).
"""
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QGridLayout, QVBoxLayout, QFileDialog, QToolBar,
    QMessageBox, QStatusBar, QScrollArea,
)

from core.image_io import load_image, save_image
from core.histogram import histogram_uint8
from core.pipeline import (
    process, ProcessResult, OutputParams,
    binarize_manual, apply_channel_curves,
)
from core.tone_curve import ChannelCurve, build_lut

from gui.image_viewer import ImagePanel
from gui.curve_view import CurveView
from gui.channel_panel import ChannelSlider
from gui.output_controls import OutputControls


CHANNEL_COLORS = ("red", "green", "blue")
CHANNEL_NAMES  = ("R", "G", "B")


class _ChannelBlock(QWidget):
    """Bloque por canal: CurveView + sliders min/max."""

    def __init__(self, name: str, color: str, parent=None):
        super().__init__(parent)
        self.name = name
        self.color = color

        self.curve = CurveView(color=color)
        self.slider = ChannelSlider(name, color)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.curve, 1)
        layout.addWidget(self.slider)


class MainWindow(QMainWindow):
    DEBOUNCE_MS = 40

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ecualización Tonal por Canales — Histogram Equalization")
        self.resize(1280, 720)
        self.showMaximized()

        self._original: np.ndarray | None = None
        self._curves: list[ChannelCurve] = [ChannelCurve() for _ in range(3)]

        self._build_toolbar()
        self._build_ui()

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(self.DEBOUNCE_MS)
        self._preview_timer.timeout.connect(self._recompute)

        self._wire_signals()

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(
            "Abre una imagen. Slider [0, 1]: 0 = identidad, 1 = ecualización completa."
        )

    # ---------- toolbar ----------
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

    # ---------- layout ----------
    def _build_ui(self) -> None:
        central = QWidget()
        grid = QGridLayout(central)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        # fila 0: imagen original
        self.panel_original = ImagePanel("Imagen original", min_size=(420, 400))
        self.panel_original.setMaximumWidth(980)
        self.panel_original.setMaximumHeight(560)
        grid.addWidget(
            self.panel_original,
            0,
            0,
            1,
            3,
            Qt.AlignmentFlag.AlignHCenter,
        )

        # fila 1: canales en escala de grises
        self._channel_panels: list[ImagePanel] = []
        for i, name in enumerate(CHANNEL_NAMES):
            p = ImagePanel(f"Canal {name}", min_size=(220, 260))
            self._channel_panels.append(p)
            grid.addWidget(p, 1, i)

        # fila 2: curvas + sliders min/max
        self._blocks: list[_ChannelBlock] = []
        for i, (name, color) in enumerate(zip(CHANNEL_NAMES, CHANNEL_COLORS)):
            b = _ChannelBlock(name, color)
            self._blocks.append(b)
            grid.addWidget(b, 2, i)
            
        # fila 3: resultado modificada + thumbnail + binarizada
        self.panel_modified = ImagePanel("Modificada", min_size=(300, 350))
        grid.addWidget(self.panel_modified, 3, 0, 2, 1)  # rowspan=2, columna 0
        
        self.panel_thumb = ImagePanel("Thumbnail (pixelado)", min_size=(240, 260))
        grid.addWidget(self.panel_thumb, 3, 1, 1, 1)
        
        self.panel_binary = ImagePanel("Binarizada", min_size=(240, 260))
        grid.addWidget(self.panel_binary, 3, 2, 1, 1)
        
        self.output_controls = OutputControls()
        grid.addWidget(self.output_controls, 4, 1, 1, 2)
        
        # ========== STRETCHES ==========
        grid.setRowStretch(0, 3)
        grid.setRowStretch(1, 2)
        grid.setRowStretch(2, 4)
        grid.setRowStretch(3, 2)
        grid.setRowStretch(4, 1)
        
        # Ajustar anchos de columnas
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        central.setMinimumWidth(1280)
        central.setMinimumHeight(1540)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(central)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setCentralWidget(scroll)

    def _wire_signals(self) -> None:
        for i, block in enumerate(self._blocks):
            block.slider.valueChanged.connect(
                lambda v, idx=i: self._on_strength_change(idx, v)
            )

        oc = self.output_controls
        oc.pixelationChanged.connect(lambda _: self._preview_timer.start())
        oc.thresholdChanged.connect(lambda _: self._preview_timer.start())
        oc.autoThresholdRequested.connect(self._on_auto_otsu)

    # ---------- handlers ----------
    def _on_strength_change(self, idx: int, v: float) -> None:
        self._curves[idx].strength = v
        self._preview_timer.start()

    # ---------- acciones de archivo ----------
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
        try:
            result = self._compute()
            save_image(path, result.modified)
            self.statusBar().showMessage(f"Guardado: {path}")
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", str(e))

    def _on_reset_all(self) -> None:
        for i, block in enumerate(self._blocks):
            block.slider.reset()
            self._curves[i].strength = 1.0
        self._preview_timer.start()

    def _on_auto_otsu(self) -> None:
        if self._original is None:
            return
        from core.pipeline import pixelated_thumbnail
        ch_r, ch_g, ch_b = apply_channel_curves(self._original, *self._current_curves())
        modified = np.stack([ch_r, ch_g, ch_b], axis=-1)
        thumb = pixelated_thumbnail(
            modified,
            self.output_controls.pixelation(),
            220,
        )
        _, otsu_value = binarize_manual(thumb, None)
        self.output_controls.set_threshold(otsu_value)
        self.statusBar().showMessage(f"Umbral Otsu calculado sobre thumbnail: {otsu_value}")

    # ---------- cómputo ----------
    def _current_curves(self) -> tuple[ChannelCurve, ChannelCurve, ChannelCurve]:
        return tuple(self._curves)  # type: ignore[return-value]

    def _current_outputs(self) -> OutputParams:
        return OutputParams(
            pixelation=self.output_controls.pixelation(),
            binary_threshold=self.output_controls.threshold(),
        )

    def _compute(self) -> ProcessResult:
        assert self._original is not None
        r, g, b = self._current_curves()
        return process(self._original, r, g, b, self._current_outputs())

    def _recompute(self) -> None:
        curves = self._current_curves()

        if self._original is None:
            for block, c in zip(self._blocks, curves):
                block.curve.set_lut(build_lut(c))
                block.curve.set_histogram(np.zeros(256, dtype=np.int64))
            return

        # LUT por canal — depende del histograma del canal ORIGINAL
        for i, (block, c) in enumerate(zip(self._blocks, curves)):
            block.curve.set_lut(build_lut(c, self._original[..., i]))

        result = self._compute()

        # canales en grises
        for panel, ch in zip(self._channel_panels, result.channels_modified):
            panel.set_image(ch)

        # histogramas del canal MODIFICADO
        for block, ch in zip(self._blocks, result.channels_modified):
            block.curve.set_histogram(histogram_uint8(ch))

        # resultados finales
        self.panel_modified.set_image(result.modified)
        self.panel_thumb.set_image(result.thumbnail)
        self.panel_binary.set_image(result.binary)
