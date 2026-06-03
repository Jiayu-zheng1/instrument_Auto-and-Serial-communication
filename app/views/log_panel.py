"""HIG-styled log output panel."""
from PyQt5.QtWidgets import QTextEdit, QWidget, QVBoxLayout, QLabel
from PyQt5.QtGui import QFont, QColor, QTextCursor
from PyQt5.QtCore import Qt
from app.views.theme import Colors, FONT_MONO, FONT_CAPTION_1, BORDER_RADIUS, MARGIN


class LogPanel(QWidget):
    """White-background real-time log viewer — HIG clean style."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup()

    def _setup(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header
        header = QLabel("Log")
        header.setFont(QFont(FONT_MONO.split(",")[0].strip('"'), 11))
        header.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; padding: 0 {MARGIN}px;")
        layout.addWidget(header)

        # Log output — white background
        self._auto_scroll = True  # 默认启用，由外部同步实际配置
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QFont(FONT_MONO.split(",")[0].strip('"'), 11))
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {Colors.LOG_BG};
                color: {Colors.LOG_TEXT};
                border: 1px solid {Colors.SEPARATOR};
                border-radius: {BORDER_RADIUS}px;
                padding: 10px 14px;
                selection-background-color: {Colors.PRIMARY};
                selection-color: white;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 6px;
                margin: 0;
            }}
            QScrollBar::handle:vertical {{
                background: {Colors.TEXT_TERTIARY};
                border-radius: 3px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {Colors.TEXT_SECONDARY};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        layout.addWidget(self.text_edit)

    def set_auto_scroll(self, enabled: bool):
        """设置是否自动滚动到底部。"""
        self._auto_scroll = enabled

    def append_log(self, message: str):
        self.text_edit.append(message)
        if self._auto_scroll:
            self.text_edit.moveCursor(QTextCursor.End)

    def clear_log(self):
        self.text_edit.clear()
