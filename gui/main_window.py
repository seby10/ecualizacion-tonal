"""
Ventana principal — Redistribución de Rango por Canal.

Organización en dos pestañas:
  - Pestaña 1: «Ecualización»
      Imagen original + histogramas (original vs. modificado) por canal + sliders
  - Pestaña 2: «Resultados»
      Imagen modificada (R+G+B), thumbnail pixelado, imagen binarizada,
      controles de pixelación y umbral.

Pipeline: original → LUT por canal → modificada → thumbnail pixelado → binarizada.
"""
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QFont, QPalette, QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout,
    QFileDialog, QToolBar, QMessageBox, QStatusBar, QScrollArea,
    QTabWidget, QLabel, QFrame, QSplitter,
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

# ── paleta de colores del tema oscuro ────────────────────────────────
_BG_DARK  = "#1e1e2e"
_BG_MID   = "#252536"
_BG_CARD  = "#313244"
_FG       = "#cdd6f4"
_ACCENT   = "#89b4fa"
_BORDER   = "#45475a"

_DARK_STYLESHEET = f"""
    QMainWindow {{
        background-color: {_BG_DARK};
    }}
    QToolBar {{
        background: {_BG_MID};
        border-bottom: 1px solid {_BORDER};
        spacing: 8px;
        padding: 4px 8px;
    }}
    QToolBar QToolButton {{
        background: {_BG_CARD};
        color: {_FG};
        border: 1px solid {_BORDER};
        border-radius: 4px;
        padding: 5px 14px;
        font-size: 13px;
        font-weight: bold;
    }}
    QToolBar QToolButton:hover {{
        background: {_ACCENT};
        color: {_BG_DARK};
    }}
    QTabWidget::pane {{
        background: {_BG_DARK};
        border: 1px solid {_BORDER};
        border-top: none;
    }}
    QTabBar::tab {{
        background: {_BG_MID};
        color: {_FG};
        padding: 10px 28px;
        font-size: 14px;
        font-weight: bold;
        border: 1px solid {_BORDER};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background: {_BG_DARK};
        color: {_ACCENT};
        border-bottom: 2px solid {_ACCENT};
    }}
    QTabBar::tab:hover {{
        background: {_BG_CARD};
    }}
    QScrollArea {{
        background: {_BG_DARK};
        border: none;
    }}
    QLabel {{
        color: {_FG};
    }}
    QFrame {{
        color: {_FG};
    }}
    QStatusBar {{
        background: {_BG_MID};
        color: {_FG};
        border-top: 1px solid {_BORDER};
        font-size: 12px;
        padding: 3px 10px;
    }}
"""


class _ChannelBlock(QWidget):
    """Bloque por canal: histogramas (orig | mod) + 4 sliders."""

    def __init__(self, name: str, color: str, parent=None):
        super().__init__(parent)
        self.name  = name
        self.color = color

        self.curve  = CurveView(color=color)
        self.slider = ChannelSlider(name, color)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.curve, 1)
        layout.addWidget(self.slider)


class _SectionTitle(QLabel):
    """Etiqueta grande para secciones dentro de las pestañas."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {_ACCENT}; "
            f"padding: 6px 0; letter-spacing: 1px;"
        )


class MainWindow(QMainWindow):
    DEBOUNCE_MS = 40

    def __init__(self):
        super().__init__()
        self.setWindowTitle(
            "Redistribución Tonal por Canal — Preprocesamiento para Visión por Computadora"
        )
        self.resize(1280, 720)
        self.showMaximized()

        self._original: np.ndarray | None = None
        self._curves: list[ChannelCurve] = [ChannelCurve() for _ in range(3)]

        self.setStyleSheet(_DARK_STYLESHEET)

        self._build_toolbar()
        self._build_ui()

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(self.DEBOUNCE_MS)
        self._preview_timer.timeout.connect(self._recompute)

        self._wire_signals()

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(
            "Abre una imagen. "
            "Usa 'Origen desde/hasta' para seleccionar el pico del histograma, "
            "y 'Destino desde/hasta' para elegir a dónde moverlo."
        )

    # ---------- toolbar ----------
    def _build_toolbar(self) -> None:
        tb = QToolBar("Principal")
        tb.setMovable(False)
        self.addToolBar(tb)

        act_open = QAction("📂  Abrir imagen", self)
        act_open.triggered.connect(self._on_open)
        tb.addAction(act_open)

        act_save = QAction("💾  Guardar modificada", self)
        act_save.triggered.connect(self._on_save)
        tb.addAction(act_save)

        tb.addSeparator()

        act_reset = QAction("↺  Reset todo", self)
        act_reset.triggered.connect(self._on_reset_all)
        tb.addAction(act_reset)

        tb.addSeparator()

        act_auto = QAction("⚡ Auto (percentil 2/98)", self)
        act_auto.setToolTip(
            "Ajusta automáticamente from_min/from_max al percentil 2%/98% "
            "de cada canal y mapea al rango completo [0, 255]."
        )
        act_auto.triggered.connect(self._on_auto)
        tb.addAction(act_auto)

    # ---------- layout con pestañas ----------
    def _build_ui(self) -> None:
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # ════════════════════════════════════════════════════════════
        # PESTAÑA 1: ECUALIZACIÓN
        # ════════════════════════════════════════════════════════════
        tab1_widget = QWidget()
        tab1_layout = QVBoxLayout(tab1_widget)
        tab1_layout.setContentsMargins(10, 10, 10, 10)
        tab1_layout.setSpacing(8)

        # — título de sección —
        tab1_layout.addWidget(_SectionTitle("Imagen Original"))

        # — imagen original centrada —
        self.panel_original = ImagePanel("Imagen original", min_size=(400, 340))
        self.panel_original.setMaximumWidth(900)
        self.panel_original.setMaximumHeight(480)
        orig_row = QHBoxLayout()
        orig_row.addStretch(1)
        orig_row.addWidget(self.panel_original)
        orig_row.addStretch(1)
        tab1_layout.addLayout(orig_row)

        # — separador visual —
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.Shape.HLine)
        sep1.setStyleSheet(f"color: {_BORDER};")
        tab1_layout.addWidget(sep1)

        # — título de histogramas —
        tab1_layout.addWidget(_SectionTitle("Histogramas y Redistribución por Canal"))

        # — canales en escala de grises (vista individual) —
        chan_img_row = QHBoxLayout()
        chan_img_row.setSpacing(8)
        self._channel_panels: list[ImagePanel] = []
        for name in CHANNEL_NAMES:
            p = ImagePanel(f"Canal {name} (modificado)", min_size=(180, 160))
            self._channel_panels.append(p)
            chan_img_row.addWidget(p, 1)
        tab1_layout.addLayout(chan_img_row)

        # — bloques de histograma + sliders por canal —
        self._blocks: list[_ChannelBlock] = []
        for name, color in zip(CHANNEL_NAMES, CHANNEL_COLORS):
            b = _ChannelBlock(name, color)
            self._blocks.append(b)
            tab1_layout.addWidget(b)

        # envolver en scroll
        tab1_scroll = QScrollArea()
        tab1_scroll.setWidgetResizable(True)
        tab1_scroll.setWidget(tab1_widget)
        tab1_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        tab1_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.tabs.addTab(tab1_scroll, "🎨  Ecualización")

        # ════════════════════════════════════════════════════════════
        # PESTAÑA 2: RESULTADOS
        # ════════════════════════════════════════════════════════════
        tab2_widget = QWidget()
        tab2_layout = QVBoxLayout(tab2_widget)
        tab2_layout.setContentsMargins(10, 10, 10, 10)
        tab2_layout.setSpacing(12)

        tab2_layout.addWidget(_SectionTitle("Resultados del Preprocesamiento"))

        # — fila de imágenes: modificada | thumbnail | binarizada —
        img_row = QHBoxLayout()
        img_row.setSpacing(12)

        self.panel_modified = ImagePanel(
            "Imagen Modificada (R+G+B)", min_size=(300, 300))
        img_row.addWidget(self.panel_modified, 2)

        self.panel_thumb = ImagePanel(
            "Thumbnail Pixelado", min_size=(250, 250))
        img_row.addWidget(self.panel_thumb, 1)

        self.panel_binary = ImagePanel(
            "Binarizada (blanco/negro)", min_size=(250, 250))
        img_row.addWidget(self.panel_binary, 1)

        tab2_layout.addLayout(img_row, 1)

        # — separador —
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {_BORDER};")
        tab2_layout.addWidget(sep2)

        # — controles de salida —
        tab2_layout.addWidget(_SectionTitle("Controles de Salida"))

        self.output_controls = OutputControls()
        tab2_layout.addWidget(self.output_controls)

        tab2_scroll = QScrollArea()
        tab2_scroll.setWidgetResizable(True)
        tab2_scroll.setWidget(tab2_widget)
        tab2_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        tab2_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.tabs.addTab(tab2_scroll, "📊  Resultados")

        self.setCentralWidget(self.tabs)

    def _wire_signals(self) -> None:
        for i, block in enumerate(self._blocks):
            block.slider.rangeChanged.connect(
                lambda fm, fM, tm, tM, trans, idx=i:
                    self._on_range_change(idx, fm, fM, tm, tM, trans)
            )

        oc = self.output_controls
        oc.pixelationChanged.connect(lambda _: self._preview_timer.start())
        oc.thresholdChanged.connect(lambda _: self._preview_timer.start())
        oc.autoThresholdRequested.connect(self._on_auto_otsu)

    # ---------- handlers ----------
    def _on_range_change(self, idx: int,
                         from_min: int, from_max: int,
                         to_min: int, to_max: int, transfer: float) -> None:
        c = self._curves[idx]
        c.from_min = from_min
        c.from_max = from_max
        c.to_min   = to_min
        c.to_max   = to_max
        c.transfer_ratio = transfer
        self._blocks[idx].curve.set_window(from_min, from_max, to_min, to_max)
        self._preview_timer.start()

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
            f"Cargada: {Path(path).name}   {img.shape[1]}×{img.shape[0]}  —  "
            "Selecciona el pico (naranja) y elige a dónde moverlo (azul)."
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
            self._curves[i] = ChannelCurve()

    def _on_auto(self) -> None:
        """Ajusta from_min/from_max al percentil 2/98 de cada canal → to [0, 255]."""
        if self._original is None:
            return
        for i in range(3):
            ch = self._original[..., i]
            lo = int(np.percentile(ch, 2))
            hi = int(np.percentile(ch, 98))
            lo = max(0, min(lo, 254))
            hi = max(lo + 1, min(hi, 255))
            self._curves[i].from_min = lo
            self._curves[i].from_max = hi
            self._curves[i].to_min   = 0
            self._curves[i].to_max   = 255
            self._curves[i].transfer_ratio = 1.0
            self._blocks[i].slider.set_values(lo, hi, 0, 255, 1.0)
            self._blocks[i].curve.set_window(lo, hi, 0, 255)
        self.statusBar().showMessage(
            "Auto-remap aplicado: percentil 2%→0 y 98%→255 por canal."
        )

    def _on_auto_otsu(self) -> None:
        if self._original is None:
            return
        from core.pipeline import pixelated_thumbnail
        ch_r, ch_g, ch_b = apply_channel_curves(self._original, *self._current_curves())
        modified = np.stack([ch_r, ch_g, ch_b], axis=-1)
        thumb = pixelated_thumbnail(
            modified, self.output_controls.pixelation(), 220,
        )
        _, otsu_value = binarize_manual(thumb, None)
        self.output_controls.set_threshold(otsu_value)
        self.statusBar().showMessage(
            f"Umbral Otsu calculado sobre thumbnail: {otsu_value}"
        )

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
                block.curve.set_window(c.from_min, c.from_max, c.to_min, c.to_max)
                block.curve.set_histogram_orig(np.zeros(256, dtype=np.int64))
                block.curve.set_histogram_mod(np.zeros(256, dtype=np.int64))
            return

        result = self._compute()

        for i, (block, c) in enumerate(zip(self._blocks, curves)):
            # LUT actual (ya no se dibuja, pero se mantiene la interfaz)
            block.curve.set_lut(build_lut(c))
            block.curve.set_window(c.from_min, c.from_max, c.to_min, c.to_max)

            # histograma ORIGINAL del canal
            block.curve.set_histogram_orig(
                histogram_uint8(self._original[..., i])
            )
            # histograma MODIFICADO del canal
            block.curve.set_histogram_mod(
                histogram_uint8(result.channels_modified[i])
            )

        # paneles de canal en escala de grises
        for panel, ch in zip(self._channel_panels, result.channels_modified):
            panel.set_image(ch)

        # resultados finales
        self.panel_modified.set_image(result.modified)
        self.panel_thumb.set_image(result.thumbnail)
        self.panel_binary.set_image(result.binary)