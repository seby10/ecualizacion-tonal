"""
Controles globales para las vistas derivadas:
  * Slider de pixelación del thumbnail (factor 1..32).
  * Slider de umbral de binarización (0..255) + botón "Auto (Otsu)".
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QFrame,
)

_BG_CARD  = "#313244"
_BG_DARK  = "#1e1e2e"
_BORDER   = "#45475a"
_FG       = "#cdd6f4"
_FG_DIM   = "#6c7086"
_ACCENT   = "#89b4fa"
_GREEN    = "#a6e3a1"


class _RangedSlider(QWidget):
    valueChanged = Signal(int)

    def __init__(self, title: str, minimum: int, maximum: int, default: int,
                 accent: str = _ACCENT, parent=None):
        super().__init__(parent)

        self._title = QLabel(title)
        self._title.setStyleSheet(
            f"font-weight: bold; font-size: 12px; color: {accent}; "
            "background: transparent; border: none;"
        )

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(minimum, maximum)
        self._slider.setValue(default)
        self._slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._slider.setTickInterval(max(1, (maximum - minimum) // 10))
        self._slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 6px;
                background: {_BORDER};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {accent};
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QSlider::sub-page:horizontal {{
                background: {accent};
                border-radius: 3px;
                opacity: 0.5;
            }}
        """)
        self._slider.valueChanged.connect(self._on_change)

        self._min_label = QLabel(str(minimum))
        self._max_label = QLabel(str(maximum))
        self._min_label.setStyleSheet(f"color: {_FG_DIM}; font-size: 11px; border: none;")
        self._max_label.setStyleSheet(f"color: {_FG_DIM}; font-size: 11px; border: none;")

        self._value_label = QLabel(str(default))
        self._value_label.setMinimumWidth(50)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_label.setStyleSheet(
            f"background: {_BG_DARK}; border: 1px solid {_BORDER}; "
            f"padding: 3px 6px; border-radius: 4px; color: {_FG}; "
            "font-family: monospace; font-size: 13px; font-weight: bold;"
        )

        row = QHBoxLayout()
        row.addWidget(self._min_label)
        row.addWidget(self._slider, 1)
        row.addWidget(self._max_label)
        row.addWidget(self._value_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.addWidget(self._title)
        layout.addLayout(row)

    def _on_change(self, v: int) -> None:
        self._value_label.setText(str(v))
        self.valueChanged.emit(v)

    def value(self) -> int:
        return self._slider.value()

    def set_value(self, v: int) -> None:
        self._slider.setValue(v)
        self._value_label.setText(str(v))


class OutputControls(QFrame):
    """
    Emite:
      pixelationChanged(int)
      thresholdChanged(int)
      autoThresholdRequested()  → el consumidor debe setear umbral = Otsu.
    """
    pixelationChanged = Signal(int)
    thresholdChanged = Signal(int)
    autoThresholdRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet(
            f"OutputControls {{ background: {_BG_CARD}; "
            f"border: 1px solid {_BORDER}; border-radius: 8px; }}"
        )

        self.pix = _RangedSlider("📐  Pixelación del thumbnail", 1, 32, 4,
                                  accent=_GREEN)
        self.thr = _RangedSlider("⚪  Umbral de binarización (0–255)", 0, 255, 128,
                                  accent="#f38ba8")

        self.btn_auto = QPushButton("⚡ Auto (Otsu)")
        self.btn_auto.setToolTip("Calcula el umbral óptimo con Otsu "
                                 "sobre la imagen modificada actual.")
        self.btn_auto.setStyleSheet(f"""
            QPushButton {{
                background: {_ACCENT};
                color: {_BG_DARK};
                border: none;
                border-radius: 6px;
                padding: 8px 18px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: #b4d0fb;
            }}
            QPushButton:pressed {{
                background: #6c9ef0;
            }}
        """)
        self.btn_auto.clicked.connect(self.autoThresholdRequested.emit)

        self.pix.valueChanged.connect(self.pixelationChanged.emit)
        self.thr.valueChanged.connect(self.thresholdChanged.emit)

        right = QHBoxLayout()
        right.addWidget(self.thr, 1)
        right.addWidget(self.btn_auto)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self.pix, 1)
        layout.addSpacing(20)
        layout.addLayout(right, 1)

    def set_threshold(self, v: int) -> None:
        self.thr.set_value(v)

    def pixelation(self) -> int:
        return self.pix.value()

    def threshold(self) -> int:
        return self.thr.value()
