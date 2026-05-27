"""HIG-compliant main window — 原生菜单栏 + 键盘快捷键 + 仪器副窗口。"""

import csv
import os
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QSplitter,
    QMessageBox,
    QMenuBar,
    QMenu,
    QAction,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence
from app.views.theme import Colors, FONT_FAMILY, stylesheet
from app.views.control_bar import ControlBar
from app.views.status_header import StatusHeader
from app.views.test_table import TestTable
from app.views.log_panel import LogPanel
from app.views.instrument_settings import InstrumentSettingsDialog
from app.controllers.test_runner import TestRunner
from app.controllers.log_controller import LogController
from app.controllers.instrument_manager import InstrumentManager
from app.utils.constants import LOG_DIR


class MainWindow(QMainWindow):
    """Primary application window with native macOS menu bar."""

    def __init__(self):
        super().__init__()
        self._csv_data: list[dict] = []
        self._runner: TestRunner = None
        self._log_ctrl = LogController(LOG_DIR)

        self._instr_mgr = InstrumentManager.instance()
        self._instr_dialog: InstrumentSettingsDialog | None = None

        self.setWindowTitle("Read Data")
        self.resize(1024, 768)
        self.setMinimumSize(1300, 640)
        self.setUnifiedTitleAndToolBarOnMac(True)
        self.setStyleSheet(stylesheet())

        self._build_ui()
        self._build_menu_bar()
        self._load_csv()
        self._init_log()
        self._connect_signals()
        self._instr_mgr.start_auto_check()

    # ── UI 构建 ──────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.control_bar = ControlBar()
        root.addWidget(self.control_bar)

        self.status_header = StatusHeader()
        root.addWidget(self.status_header)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {Colors.SEPARATOR}; }}"
        )

        self.test_table = TestTable()
        self.log_panel = LogPanel()

        splitter.addWidget(self.test_table)
        splitter.addWidget(self.log_panel)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([600, 400])

        root.addWidget(splitter, 1)

    # ── 原生菜单栏 (macOS HIG Rule 1.1) ────────────────────────────────

    def _build_menu_bar(self):
        mb = self.menuBar()

        # ── App 菜单 ──
        app_menu = mb.addMenu("Read Data")
        about_action = QAction("关于 Read Data", self)
        app_menu.addAction(about_action)

        app_menu.addSeparator()
        settings_action = QAction("仪器设置…", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._show_instrument_settings)
        app_menu.addAction(settings_action)

        app_menu.addSeparator()
        quit_action = QAction("退出 Read Data", self)
        quit_action.setShortcut(QKeySequence.Quit)
        quit_action.triggered.connect(self.close)
        app_menu.addAction(quit_action)

        # ── 文件 菜单 ──
        file_menu = mb.addMenu("文件")
        export_action = QAction("导出日志…", self)
        export_action.setShortcut(QKeySequence("Ctrl+E"))
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        close_action = QAction("关闭窗口", self)
        close_action.setShortcut(QKeySequence.Close)
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)

        # ── 编辑 菜单 ──
        edit_menu = mb.addMenu("编辑")
        undo_action = QAction("撤销", self)
        undo_action.setShortcut(QKeySequence.Undo)
        edit_menu.addAction(undo_action)
        redo_action = QAction("重做", self)
        redo_action.setShortcut(QKeySequence.Redo)
        edit_menu.addAction(redo_action)
        edit_menu.addSeparator()
        cut_action = QAction("剪切", self)
        cut_action.setShortcut(QKeySequence.Cut)
        edit_menu.addAction(cut_action)
        copy_action = QAction("复制", self)
        copy_action.setShortcut(QKeySequence.Copy)
        edit_menu.addAction(copy_action)
        paste_action = QAction("粘贴", self)
        paste_action.setShortcut(QKeySequence.Paste)
        edit_menu.addAction(paste_action)
        select_all = QAction("全选", self)
        select_all.setShortcut(QKeySequence.SelectAll)
        edit_menu.addAction(select_all)

        # ── 视图 菜单 ──
        view_menu = mb.addMenu("视图")
        instr_action = QAction("仪器设置…", self)
        instr_action.setShortcut(QKeySequence("Ctrl+,"))
        instr_action.triggered.connect(self._show_instrument_settings)
        view_menu.addAction(instr_action)

        # ── 窗口 菜单 ──
        window_menu = mb.addMenu("窗口")
        minimize_action = QAction("最小化", self)
        minimize_action.setShortcut(QKeySequence("Ctrl+M"))
        minimize_action.triggered.connect(self.showMinimized)
        window_menu.addAction(minimize_action)

    # ── CSV 加载 ───────────────────────────────────────────────────────

    def _load_csv(self):
        limits_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "resources", "Limits.csv"
        )
        if not os.path.exists(limits_path):
            limits_path = os.path.join(
                os.path.dirname(__file__), "..", "Resource", "Limits.csv"
            )
        try:
            with open(limits_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self._csv_data = [
                    {k: (v if v else "") for k, v in row.items()} for row in reader
                ]
            self.test_table.load_config(self._csv_data)
        except FileNotFoundError:
            QMessageBox.warning(
                self, "Config Error", f"Limits.csv not found at {limits_path}"
            )

    def _init_log(self):
        self._log_ctrl.initialize()
        self._log_ctrl.bind_signal(self.log_panel.append_log)

    # ── 信号连接 ──────────────────────────────────────────────────────

    def _connect_signals(self):
        self.control_bar.start_btn.clicked.connect(self._start_test)
        self.control_bar.sn_input.returnPressed.connect(self._start_test)
        self.control_bar.signal_gear_clicked.connect(self._show_instrument_settings)
        self._instr_mgr.signal_all_checked.connect(self._on_all_instruments_checked)

    def _show_instrument_settings(self):
        """打开仪器设置对话框（延迟创建，信号一次连接）。"""
        if self._instr_dialog is None:
            dlg = InstrumentSettingsDialog(self)
            dlg.signal_reconnect.connect(self._on_instr_reconnect)
            self._instr_mgr.signal_device_status.connect(dlg.set_device_status)
            self._instr_dialog = dlg
        self._instr_dialog.show()
        self._instr_dialog.raise_()
        self._instr_dialog.activateWindow()

    def _on_instr_reconnect(self, device_name: str):
        """重连指定仪器。空字符串 = 全部重连。"""
        if device_name:
            self._instr_mgr.reconnect_device(device_name)
        else:
            self._instr_mgr.reconnect_all()

    def _on_all_instruments_checked(self):
        mgr = self._instr_mgr
        parts = []
        parts.append("34970A ✓" if mgr.dmm_connected else "34970A ✗")
        parts.append("IT6382 ✓" if mgr.ps_connected else "IT6382 ✗")
        parts.append("Relayboard ✓" if mgr.relay_connected else "Relayboard ✗")
        self.log_panel.append_log(f"仪器检测完成: {' | '.join(parts)}")

    # ── 测试流程 ──────────────────────────────────────────────────────

    def _start_test(self):
        sn = self.control_bar.sn_input.text().strip()
        if not sn:
            QMessageBox.warning(self, "Input Required", "Please scan or enter an SN.")
            return

        self.control_bar.set_running(True)
        self.status_header.set_running()
        self.test_table.clear_results()
        self.log_panel.clear_log()
        self.control_bar.start_timer()

        self._runner = TestRunner(self._csv_data, self._log_ctrl)
        self._runner.ScanSN = sn
        self._runner.signal_value.connect(self.test_table.set_value)
        self._runner.signal_result.connect(self.test_table.set_result)
        self._runner.signal_color.connect(self.test_table.set_result_color)
        self._runner.signal_status.connect(self._on_status)
        self._runner.signal_stop.connect(self._on_test_completed)
        self._runner.signal_display.connect(self._on_display_sn)
        self._runner.start()

    def _on_status(self, passed: bool):
        self.status_header.add_result(passed)
        if passed:
            self.status_header.set_pass()
        else:
            self.status_header.set_fail()

    def _on_test_completed(self):
        self.control_bar.stop_timer()
        self.control_bar.set_running(False)
        self.control_bar.sn_input.clear()
        self.control_bar.sn_input.setFocus()

    def _on_display_sn(self, scan_sn: str, fgsn: str):
        self.statusBar().showMessage(f"ScanSN: {scan_sn}  |  FGSN: {fgsn}")

    def closeEvent(self, event):
        self._instr_mgr.shutdown()
        super().closeEvent(event)
