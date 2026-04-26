"""
Controles globales para las vistas derivadas:
  * Slider de pixelación del thumbnail (factor 1..32).
  * Slider de umbral de binarización (0..255) + botón "Auto (Otsu)".
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QFrame,
)


class _RangedSlider(QWidget):
    valueChanged = Signal(int)

    def __init__(self, title: str, minimum: int, maximum: int, default: int,
                 parent=None):
        super().__init__(parent)
        self._title = QLabel(title)
        self._title.setStyleSheet("font-weight: bold;")

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(minimum, maximum)
        self._slider.setValue(default)
        self._slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._slider.setTickInterval(max(1, (maximum - minimum) // 10))
        self._slider.valueChanged.connect(self._on_change)

        self._min_label = QLabel(str(minimum))
        self._max_label = QLabel(str(maximum))
        self._min_label.setStyleSheet("color: #888;")
        self._max_label.setStyleSheet("color: #888;")

        self._value_label = QLabel(str(default))
        self._value_label.setMinimumWidth(50)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_label.setStyleSheet(
            "background: #eef; border: 1px solid #aac; padding: 2px;"
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

        self.pix = _RangedSlider("Pixelación del thumbnail", 1, 32, 4)
        self.thr = _RangedSlider("Umbral de binarización (0–255)", 0, 255, 128)

        self.btn_auto = QPushButton("Auto (Otsu)")
        self.btn_auto.setToolTip("Calcula el umbral óptimo con Otsu "
                                 "sobre la imagen modificada actual.")
        self.btn_auto.clicked.connect(self.autoThresholdRequested.emit)

        self.pix.valueChanged.connect(self.pixelationChanged.emit)
        self.thr.valueChanged.connect(self.thresholdChanged.emit)

        right = QHBoxLayout()
        right.addWidget(self.thr, 1)
        right.addWidget(self.btn_auto)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.pix, 1)
        layout.addSpacing(20)
        layout.addLayout(right, 1)

    def set_threshold(self, v: int) -> None:
        self.thr.set_value(v)

    def pixelation(self) -> int:
        return self.pix.value()

    def threshold(self) -> int:
        return self.thr.value()
