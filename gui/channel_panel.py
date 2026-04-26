"""
Control de un canal: cuatro sliders para definir el remapeo de rango.

    from_min, from_max  →  rango de entrada (zona del histograma a mover)
    to_min,   to_max    →  rango destino (donde queremos poner esos píxeles)

La LUT resultante interpola linealmente [from_min, from_max] → [to_min, to_max].
El resto queda en identidad. No se pierden píxeles.
"""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSlider, QPushButton, QFrame,
)

_BG_CARD   = "#313244"
_BG_DARK   = "#1e1e2e"
_BORDER    = "#45475a"
_FG        = "#cdd6f4"
_FG_DIM    = "#6c7086"
_ORANGE    = "#fab387"
_BLUE      = "#89b4fa"

_CHANNEL_ACCENT = {
    "red":   "#f38ba8",
    "green": "#a6e3a1",
    "blue":  "#89b4fa",
}


def _make_slider(lo: int, hi: int, val: int) -> QSlider:
    s = QSlider(Qt.Orientation.Horizontal)
    s.setRange(lo, hi)
    s.setValue(val)
    s.setTickPosition(QSlider.TickPosition.TicksBelow)
    s.setTickInterval(32)
    s.setStyleSheet(f"""
        QSlider::groove:horizontal {{
            height: 5px;
            background: {_BORDER};
            border-radius: 2px;
        }}
        QSlider::handle:horizontal {{
            background: {_FG};
            width: 14px;
            height: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }}
    """)
    return s


def _val_label(text: str, color: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setMinimumWidth(42)
    lbl.setStyleSheet(
        f"background: {_BG_DARK}; border: 1px solid {color}66; "
        f"padding: 2px 6px; border-radius: 4px; font-family: monospace; "
        f"font-size: 13px; font-weight: bold; color: {color};"
    )
    return lbl


class ChannelSlider(QWidget):
    """
    Cuatro sliders: from_min / from_max / to_min / to_max.
    Emite rangeChanged(from_min, from_max, to_min, to_max).
    """
    rangeChanged = Signal(int, int, int, int)

    def __init__(self, channel_name: str, color: str, parent=None):
        super().__init__(parent)
        self._color = color
        self._busy = False

        accent = _CHANNEL_ACCENT.get(color, _FG)

        self.setStyleSheet(
            f"ChannelSlider {{ background: {_BG_CARD}; "
            f"border: 1px solid {_BORDER}; border-radius: 8px; }}"
        )

        # --- título ---
        title = QLabel(f"Canal {channel_name} — Redistribución de Rango")
        f = title.font(); f.setBold(True); f.setPointSize(11); title.setFont(f)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"color: {accent}; background: transparent; border: none; padding: 4px;"
        )

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {_BORDER};")

        # --- sliders ---
        self._s = {
            "from_min": _make_slider(0, 254, 0),
            "from_max": _make_slider(1, 255, 255),
            "to_min":   _make_slider(0, 254, 0),
            "to_max":   _make_slider(1, 255, 255),
        }

        self._v = {
            "from_min": _val_label("0",   _ORANGE),
            "from_max": _val_label("255", _ORANGE),
            "to_min":   _val_label("0",   _BLUE),
            "to_max":   _val_label("255", _BLUE),
        }

        rows = [
            ("Origen desde",  "from_min", _ORANGE, "0",   "254"),
            ("Origen hasta",  "from_max", _ORANGE, "1",   "255"),
            ("Destino desde", "to_min",   _BLUE,   "0",   "254"),
            ("Destino hasta", "to_max",   _BLUE,   "1",   "255"),
        ]

        grid = QGridLayout()
        grid.setContentsMargins(10, 4, 10, 8)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(2, 1)

        for row_i, (lbl_text, key, clr, lo_txt, hi_txt) in enumerate(rows):
            lbl = QLabel(lbl_text)
            lbl.setStyleSheet(
                f"color: {clr}; font-size: 12px; font-weight: bold; "
                "background: transparent; border: none;"
            )
            lbl.setMinimumWidth(110)

            lo_lbl = QLabel(lo_txt)
            lo_lbl.setStyleSheet(
                f"color: {_FG_DIM}; font-size: 11px; background: transparent; border: none;"
            )
            lo_lbl.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            lo_lbl.setMinimumWidth(22)

            hi_lbl = QLabel(hi_txt)
            hi_lbl.setStyleSheet(
                f"color: {_FG_DIM}; font-size: 11px; background: transparent; border: none;"
            )
            hi_lbl.setAlignment(
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            hi_lbl.setMinimumWidth(22)

            grid.addWidget(lbl,             row_i, 0)
            grid.addWidget(lo_lbl,          row_i, 1)
            grid.addWidget(self._s[key],    row_i, 2)
            grid.addWidget(hi_lbl,          row_i, 3)
            grid.addWidget(self._v[key],    row_i, 4)

        # --- botón reset ---
        reset_btn = QPushButton("↺  Reset canal")
        reset_btn.setFixedWidth(130)
        reset_btn.setToolTip("Volver a identidad (sin redistribución)")
        reset_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_BORDER};
                color: {_FG};
                border: none;
                border-radius: 5px;
                padding: 6px 12px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {accent};
                color: {_BG_DARK};
            }}
        """)
        reset_btn.clicked.connect(self.reset)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(reset_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.addWidget(title)
        layout.addWidget(sep)
        layout.addLayout(grid)
        layout.addLayout(bottom)

        # conexiones
        for key, sl in self._s.items():
            sl.valueChanged.connect(lambda v, k=key: self._on_change(k, v))

    def _on_change(self, key: str, v: int) -> None:
        if self._busy:
            return
        self._busy = True

        # garantizar from_min < from_max y to_min < to_max
        fm = self._s["from_min"].value()
        fM = self._s["from_max"].value()
        tm = self._s["to_min"].value()
        tM = self._s["to_max"].value()

        if key == "from_min" and v >= fM:
            self._s["from_max"].setValue(min(v + 1, 255)); fM = v + 1
        if key == "from_max" and v <= fm:
            self._s["from_min"].setValue(max(v - 1, 0)); fm = v - 1
        if key == "to_min" and v >= tM:
            self._s["to_max"].setValue(min(v + 1, 255)); tM = v + 1
        if key == "to_max" and v <= tm:
            self._s["to_min"].setValue(max(v - 1, 0)); tm = v - 1

        for k, sl in self._s.items():
            self._v[k].setText(str(sl.value()))

        self._busy = False
        self.rangeChanged.emit(
            self._s["from_min"].value(), self._s["from_max"].value(),
            self._s["to_min"].value(),   self._s["to_max"].value(),
        )

    # ---------- interfaz pública ----------
    def values(self) -> tuple[int, int, int, int]:
        return (
            self._s["from_min"].value(), self._s["from_max"].value(),
            self._s["to_min"].value(),   self._s["to_max"].value(),
        )

    def set_values(self, from_min: int, from_max: int,
                   to_min: int, to_max: int) -> None:
        self._busy = True
        self._s["from_min"].setValue(max(0, min(from_min, 254)))
        self._s["from_max"].setValue(max(1, min(from_max, 255)))
        self._s["to_min"].setValue(max(0, min(to_min, 254)))
        self._s["to_max"].setValue(max(1, min(to_max, 255)))
        for k, sl in self._s.items():
            self._v[k].setText(str(sl.value()))
        self._busy = False
        self.rangeChanged.emit(*self.values())

    def reset(self) -> None:
        self.set_values(0, 255, 0, 255)