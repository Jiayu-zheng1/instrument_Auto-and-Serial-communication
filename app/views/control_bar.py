"""HIG-styled control bar — SN input, Start button, timer, logo, instrument gear."""
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QLineEdit, QPushButton, QLabel, QFrame, QTextEdit
)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
import os
from app.views.theme import (
    Colors, FONT_FAMILY, FONT_TITLE_2, FONT_BODY,
    BUTTON_HEIGHT, INPUT_HEIGHT, ELEMENT_GAP, MARGIN, BORDER_RADIUS
)
from app.utils.constants import SN_MAX_LENGTH


class ControlBar(QWidget):
    """Top control area with SN input, Start button, and elapsed timer."""

    signal_gear_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._elapsed = 0.0
        self._timer = QTimer()
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._tick)
        self._setup()

    def _setup(self):
        self.setFixedHeight(56)
        self.setStyleSheet(f"""
            ControlBar {{
                background-color: {Colors.CONTROL_BG};
                border-bottom: 1px solid {Colors.SEPARATOR};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(MARGIN, 8, MARGIN, 8)
        layout.setSpacing(ELEMENT_GAP)

        # Logo
        self.logo_label = QLabel()
        logo_path = os.path.join(os.path.dirname(__file__), "..", "..", "resources", "logo.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            if not pix.isNull():
                self.logo_label.setPixmap(pix.scaled(160, 30, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(self.logo_label)

        layout.addStretch()

        # SN Label
        sn_label = QLabel("SN:")
        sn_label.setFont(self._font(*FONT_BODY))
        layout.addWidget(sn_label)

        # SN Input
        self.sn_input = QLineEdit()
        self.sn_input.setPlaceholderText("Scan Serial Number")
        self.sn_input.setMaxLength(SN_MAX_LENGTH)
        self.sn_input.setFixedWidth(200)
        self.sn_input.setFixedHeight(INPUT_HEIGHT + 4)
        self.sn_input.setFont(self._font(*FONT_BODY))
        self.sn_input.setStyleSheet(f"""
            QLineEdit {{
                border: 1.5px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 4px 12px;
                background: {Colors.WINDOW_BG};
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 2px solid {Colors.PRIMARY};
                padding: 3px 11px;
            }}
        """)
        layout.addWidget(self.sn_input)

        # Start Button
        self.start_btn = QPushButton("Start")
        self.start_btn.setFixedHeight(BUTTON_HEIGHT + 2)
        self.start_btn.setFont(self._font(*FONT_BODY))
        self.start_btn.setCursor(Qt.PointingHandCursor)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.PRIMARY};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 24px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {Colors.PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: #0051AA;
            }}
            QPushButton:disabled {{
                background-color: {Colors.TEXT_TERTIARY};
                color: #F5F5F7;
            }}
        """)
        layout.addWidget(self.start_btn)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet(f"color: {Colors.SEPARATOR};")
        layout.addWidget(sep)

        # Timer
        timer_label = QLabel("Time:")
        timer_label.setFont(self._font(*FONT_BODY))
        layout.addWidget(timer_label)

        self.time_display = QLabel("00:00")
        self.time_display.setFont(self._font(*FONT_TITLE_2))
        self.time_display.setMinimumWidth(70)
        self.time_display.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.time_display)

        # Gear button for instrument settings
        self.gear_btn = QPushButton("⚙")
        self.gear_btn.setFixedSize(36, 36)
        self.gear_btn.setFont(self._font(*FONT_BODY))
        self.gear_btn.setCursor(Qt.PointingHandCursor)
        self.gear_btn.setToolTip("仪器设置")
        self.gear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: {BORDER_RADIUS}px;
                font-size: 18px;
                padding: 0;
            }}
            QPushButton:hover {{
                background-color: {Colors.WINDOW_BG};
                color: {Colors.PRIMARY};
                border-color: {Colors.PRIMARY};
            }}
        """)
        self.gear_btn.clicked.connect(self.signal_gear_clicked.emit)
        layout.addWidget(self.gear_btn)

    def _tick(self):
        self._elapsed += 0.1
        total_s = int(self._elapsed)
        frac = int((self._elapsed - total_s) * 1000)
        self.time_display.setText(f"{total_s // 60:02d}:{total_s % 60:02d}.{frac:03d}")

    def start_timer(self):
        self._elapsed = 0.0
        self._timer.start()

    def stop_timer(self):
        self._timer.stop()

    def set_running(self, running: bool):
        self.sn_input.setEnabled(not running)
        self.start_btn.setEnabled(not running)
        if running:
            self.start_btn.setText("Running…")
        else:
            self.start_btn.setText("Start")

    def _font(self, family: str, size: int, weight: str):
        f = QFont(family.split(",")[0].strip('"'), size)
        if weight == "Semibold":
            f.setWeight(QFont.DemiBold)
        return f
