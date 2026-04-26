"""
Control de un canal: un único slider de fuerza de ecualización.

    s = 0.0 → identidad (sin cambios)
    s = 1.0 → ecualización completa
    intermedio → blend lineal con la identidad

LUT correspondiente: lut_equalize(channel, s) — ver core.redistribution.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton


class ChannelSlider(QWidget):
    """Slider [0, 1] con etiqueta, valor y botón de reset al máximo."""
    valueChanged = Signal(float)

    _STEPS = 100  # resolución interna: 0..100 → 0.00..1.00

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
        self._slider.setRange(0, self._STEPS)
        self._slider.setValue(self._STEPS)  # default: ecualización completa
        self._slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._slider.setTickInterval(self._STEPS // 4)
        self._slider.valueChanged.connect(self._on_change)

        self._value_label = QLabel("1.00")
        self._value_label.setMinimumWidth(45)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        reset_btn = QPushButton("↺")
        reset_btn.setFixedWidth(28)
        reset_btn.setToolTip("Volver a ecualización completa (1.00)")
        reset_btn.clicked.connect(self.reset)

        min_label = QLabel("0.00")
        max_label = QLabel("1.00")
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
        self._value_label.setText(f"{v:.2f}")
        self.valueChanged.emit(v)

    def value(self) -> float:
        """Devuelve la fuerza de ecualización en [0, 1]."""
        return self._slider.value() / self._STEPS

    def reset(self) -> None:
        self._slider.setValue(self._STEPS)
