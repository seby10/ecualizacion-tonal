"""
Control de un canal: dos sliders (min_in, max_in) que definen la ventana
de contrast stretching.

    s_min ∈ [0, 254]
    s_max ∈ [1, 255]   (siempre > s_min — se hace clamp mutuo)

LUT correspondiente: lut_stretch(s_min, s_max) — ver core.redistribution.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSlider, QPushButton,
)


class ChannelSlider(QWidget):
    """Dos sliders min_in/max_in con etiquetas y reset."""
    valueChanged = Signal(int, int)  # (min_in, max_in)

    def __init__(self, channel_name: str, color: str, parent=None):
        super().__init__(parent)
        self.channel_name = channel_name

        title = QLabel(f"Canal {channel_name}")
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {color};")

        # min slider
        self._min_slider = QSlider(Qt.Orientation.Horizontal)
        self._min_slider.setRange(0, 255)
        self._min_slider.setValue(0)
        self._min_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._min_slider.setTickInterval(32)
        self._min_slider.valueChanged.connect(self._on_min_change)

        # max slider
        self._max_slider = QSlider(Qt.Orientation.Horizontal)
        self._max_slider.setRange(0, 255)
        self._max_slider.setValue(255)
        self._max_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._max_slider.setTickInterval(32)
        self._max_slider.valueChanged.connect(self._on_max_change)

        # value labels
        self._min_value_label = QLabel("0")
        self._max_value_label = QLabel("255")
        for lbl in (self._min_value_label, self._max_value_label):
            lbl.setMinimumWidth(34)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        reset_btn = QPushButton("↺")
        reset_btn.setFixedWidth(28)
        reset_btn.setToolTip("Restablecer ventana completa [0, 255]")
        reset_btn.clicked.connect(self.reset)

        min_tag = QLabel("min")
        max_tag = QLabel("max")
        for lbl in (min_tag, max_tag):
            lbl.setStyleSheet("color: #888;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setMinimumWidth(28)

        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(2)
        grid.addWidget(min_tag,                0, 0)
        grid.addWidget(self._min_slider,       0, 1)
        grid.addWidget(self._min_value_label,  0, 2)
        grid.addWidget(max_tag,                1, 0)
        grid.addWidget(self._max_slider,       1, 1)
        grid.addWidget(self._max_value_label,  1, 2)
        grid.setColumnStretch(1, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(reset_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.addWidget(title)
        layout.addLayout(grid)
        layout.addLayout(bottom)

    # ---- mutual clamp: min < max ----
    def _on_min_change(self, v: int) -> None:
        if v >= self._max_slider.value():
            self._max_slider.blockSignals(True)
            self._max_slider.setValue(min(255, v + 1))
            self._max_slider.blockSignals(False)
        self._refresh_labels()
        self._emit()

    def _on_max_change(self, v: int) -> None:
        if v <= self._min_slider.value():
            self._min_slider.blockSignals(True)
            self._min_slider.setValue(max(0, v - 1))
            self._min_slider.blockSignals(False)
        self._refresh_labels()
        self._emit()

    def _refresh_labels(self) -> None:
        self._min_value_label.setText(str(self._min_slider.value()))
        self._max_value_label.setText(str(self._max_slider.value()))

    def _emit(self) -> None:
        self.valueChanged.emit(self._min_slider.value(), self._max_slider.value())

    def value(self) -> tuple[int, int]:
        return self._min_slider.value(), self._max_slider.value()

    def reset(self) -> None:
        self._min_slider.blockSignals(True)
        self._max_slider.blockSignals(True)
        self._min_slider.setValue(0)
        self._max_slider.setValue(255)
        self._min_slider.blockSignals(False)
        self._max_slider.blockSignals(False)
        self._refresh_labels()
        self._emit()
