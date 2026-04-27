"""
Control de un canal: un único slider para max_in.

    max_in = 255 → identidad (sin cambios)
    max_in < 255 → estiramiento (aumenta el brillo)

LUT correspondiente: lut_stretch(0, max_in) — ver core.redistribution.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton


class ChannelSlider(QWidget):
    """Slider [1, 255] con etiqueta, valor y botón de reset al máximo."""
    valueChanged = Signal(int)

    def __init__(self, channel_name: str, color: str, parent=None):
        super().__init__(parent)
        self.channel_name = channel_name

        title = QLabel(f"Canal {channel_name}")
        font = title.font()
        font.setBold(True)
        title.setFont(font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {color};")

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(1, 255)
        self._slider.setValue(255)  # default: identidad
        self._slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._slider.setTickInterval(32)
        self._slider.valueChanged.connect(self._on_change)

        self._value_label = QLabel("255")
        self._value_label.setMinimumWidth(35)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        reset_btn = QPushButton("↺")
        reset_btn.setFixedWidth(28)
        reset_btn.setToolTip("Volver a la normalidad (255)")
        reset_btn.clicked.connect(self.reset)

        min_label = QLabel("1")
        max_label = QLabel("255")
        for lbl in (min_label, max_label):
            lbl.setStyleSheet("color: #888;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        row = QHBoxLayout()
        row.addWidget(min_label)
        row.addWidget(self._slider, 1)
        row.addWidget(max_label)
        row.addWidget(self._value_label)
        row.addWidget(reset_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.addWidget(title)
        layout.addLayout(row)

    def _on_change(self, raw: int) -> None:
        v = self.value()
        self._value_label.setText(str(v))
        self.valueChanged.emit(v)

    def value(self) -> int:
        """Devuelve el max_in en [1, 255]."""
        return self._slider.value()

    def reset(self) -> None:
        self._slider.setValue(255)
