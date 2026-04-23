"""
Control de un canal: un único slider centrado en 0, rango [-1, 1].

El valor del slider se interpreta como la fuerza de la curva gamma:
    s = -1 → γ = 4   (oscurece, expande sombras)
    s =  0 → γ = 1   (identidad)
    s = +1 → γ = 1/4 (aclara, expande luces)
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton


class ChannelSlider(QWidget):
    """Slider centrado con etiqueta y valor, y botón de reset al centro."""
    valueChanged = Signal(float)

    _STEPS = 200  # resolución interna: -100..+100

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
        self._slider.setRange(-self._STEPS // 2, self._STEPS // 2)
        self._slider.setValue(0)
        self._slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._slider.setTickInterval(self._STEPS // 4)
        self._slider.valueChanged.connect(self._on_change)

        self._value_label = QLabel("0.00")
        self._value_label.setMinimumWidth(45)
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        reset_btn = QPushButton("↺")
        reset_btn.setFixedWidth(28)
        reset_btn.setToolTip("Volver al centro (identidad)")
        reset_btn.clicked.connect(self.reset)

        min_label = QLabel("−1.00")
        max_label = QLabel("+1.00")
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
        self._value_label.setText(f"{v:+.2f}")
        self.valueChanged.emit(v)

    def value(self) -> float:
        """Devuelve el valor normalizado en [-1, 1]."""
        return self._slider.value() / (self._STEPS // 2)

    def reset(self) -> None:
        self._slider.setValue(0)
