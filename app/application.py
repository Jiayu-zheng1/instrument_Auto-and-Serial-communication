"""QApplication bootstrap and lifecycle."""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from app.views.main_window import MainWindow


class Application:
    """Manages QApplication lifecycle."""

    def __init__(self):
        self._qapp = None
        self._window = None

    def create(self):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        self._qapp = QApplication(sys.argv)
        self._qapp.setApplicationName("instrument_Auto-and-Serial-communication")
        self._qapp.setOrganizationName("Foxlink")
        self._window = MainWindow()

    def show(self):
        self._window.show()

    def run(self):
        return sys.exit(self._qapp.exec_())
