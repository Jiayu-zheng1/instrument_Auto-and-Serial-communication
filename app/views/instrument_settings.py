"""仪器设置对话框 — QFluentWidgets 交互控件 + 纯 QWidget 布局。"""
import serial.tools.list_ports
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QWidget, QLabel, QFrame, QSizePolicy,
)
from PyQt5.QtGui import QFont
from qfluentwidgets import (
    PrimaryPushButton, LineEdit, ComboBox, RadioButton, FluentIcon,
)
from loguru import logger
from app.views.theme import Colors, FONT_FAMILY
from app.controllers.instrument_manager import InstrumentManager


ROW_SPACING = 12


def _list_serial_ports():
    ports = [p.device for p in serial.tools.list_ports.comports()]
    return ports if ports else []


def _label(text: str, size: int = 12, bold: bool = False) -> QLabel:
    """统一标签工厂 — 颜色使用项目 Colors，不受 QFluentWidgets 主题影响。"""
    lbl = QLabel(text)
    family = FONT_FAMILY.split(",")[0].strip('"')
    f = QFont(family, size)
    if bold:
        f.setBold(True)
    lbl.setFont(f)
    lbl.setStyleSheet(
        f"color: {Colors.TEXT_PRIMARY}; background: transparent; border: none;"
    )
    return lbl


class _InstrumentRow(QFrame):
    """横向仪器卡片行。QFluentWidgets 控件 + 纯 QLabel。"""

    signal_connect = pyqtSignal(str)
    signal_disconnect = pyqtSignal(str)

    def __init__(self, device_id: str, display_name: str, port_types: list[str], parent=None):
        super().__init__(parent)
        self._device_id = device_id        # 与 InstrumentManager 匹配的 ID
        self._display_name = display_name  # 界面显示名称
        self._port_types = port_types
        self._connected = False
        self._port_combo: ComboBox | None = None
        self._addr_input: LineEdit | None = None
        self._connect_btn: PrimaryPushButton | None = None
        self._dot_lbl: QLabel | None = None
        self._status_lbl: QLabel | None = None
        self._mode_radios: dict[str, RadioButton] = {}

        self._build()

    def _build(self):
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(f"""
            _InstrumentRow {{
                background-color: {Colors.CONTROL_BG};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 10, 16, 10)
        row.setSpacing(16)

        only_one = len(self._port_types) == 1
        has_usb = "USB" in self._port_types
        has_gpib = "GPIB" in self._port_types

        # ── 组1：名称（固定宽度） ──
        name_grp = QHBoxLayout()
        name_grp.setSpacing(0)
        name_lbl = _label(self._display_name, 13, bold=True)
        name_lbl.setFixedWidth(170)
        name_grp.addWidget(name_lbl)
        row.addLayout(name_grp)

        # ── 组2：连接方式（固定宽度） ──
        mode_grp = QHBoxLayout()
        mode_grp.setSpacing(2)
        if len(self._port_types) > 1:
            for i, pt in enumerate(self._port_types):
                rb = RadioButton(pt)
                rb.setChecked(i == 0)
                rb.toggled.connect(self._make_mode_handler(pt))
                self._mode_radios[pt] = rb
                mode_grp.addWidget(rb)
        else:
            mode_lbl = _label(self._port_types[0], 12)
            mode_lbl.setFixedWidth(60)
            mode_grp.addWidget(mode_lbl)
        row.addLayout(mode_grp)

        # ── 组3：端口/地址 + 扫描（stretch 自适应） ──
        port_grp = QHBoxLayout()
        port_grp.setSpacing(6)
        self._port_combo = ComboBox()
        self._port_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        ports = _list_serial_ports()
        if ports:
            self._port_combo.addItems(ports)
        self._port_combo.setVisible(has_usb and only_one)
        port_grp.addWidget(self._port_combo, 1)

        self._addr_input = LineEdit()
        self._addr_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._addr_input.setPlaceholderText("GPIB 地址，如 11")
        self._addr_input.setVisible(has_gpib and only_one)
        port_grp.addWidget(self._addr_input, 1)
        row.addLayout(port_grp, 1)  # stretch=1 自适应

        # ── 组4：连接按钮 + 状态（固定宽度） ──
        action_grp = QHBoxLayout()
        action_grp.setSpacing(8)
        self._connect_btn = PrimaryPushButton("连接")
        self._connect_btn.setFixedSize(80, 32)
        self._connect_btn.setStyleSheet("font-size: 12px;")
        self._connect_btn.clicked.connect(self._on_connect_clicked)
        action_grp.addWidget(self._connect_btn)

        self._dot_lbl = _label("●", 11)
        self._dot_lbl.setFixedWidth(14)
        self._dot_lbl.setAlignment(Qt.AlignCenter)
        self._dot_lbl.setStyleSheet(f"color: {Colors.TEXT_TERTIARY}; font-size: 11px; background: transparent;")
        action_grp.addWidget(self._dot_lbl)

        self._status_lbl = _label("未连接", 11)
        self._status_lbl.setFixedWidth(55)
        self._status_lbl.setStyleSheet(f"color: {Colors.TEXT_TERTIARY}; font-size: 11px; background: transparent;")
        action_grp.addWidget(self._status_lbl)
        row.addLayout(action_grp)

    def _make_mode_handler(self, mode: str):
        def handler(checked: bool):
            if checked:
                self._port_combo.setVisible(mode == "USB")
                self._addr_input.setVisible(mode == "GPIB")
        return handler

    def _on_connect_clicked(self):
        if self._connected:
            logger.info(f"[设置页] 断开 {self._device_id}, 模式={self.get_mode()}")
            self.signal_disconnect.emit(self._device_id)
        else:
            port = self.get_port_value()
            logger.info(f"[设置页] 连接 {self._device_id}, 模式={self.get_mode()}, 端口={port}")
            self.signal_connect.emit(self._device_id)

    def get_mode(self) -> str:
        if self._mode_radios:
            for pt, rb in self._mode_radios.items():
                if rb.isChecked():
                    return pt.lower()
        return self._port_types[0].lower()

    def get_port_value(self) -> str:
        if self.get_mode() == "usb":
            return self._port_combo.currentText().strip()
        return self._addr_input.text().strip()

    def set_port_value(self, value: str):
        if self.get_mode() == "usb":
            idx = self._port_combo.findText(value)
            if idx >= 0:
                self._port_combo.setCurrentIndex(idx)
            elif value:
                self._port_combo.insertItem(0, value)
                self._port_combo.setCurrentIndex(0)
        else:
            self._addr_input.setText(value)

    def set_mode(self, mode: str):
        mode = mode.upper()
        rb = self._mode_radios.get(mode)
        if rb:
            rb.setChecked(True)
        self._port_combo.setVisible(mode == "USB")
        self._addr_input.setVisible(mode == "GPIB")

    def set_status(self, connected: bool, detail: str):
        self._connected = connected
        if connected:
            self._dot_lbl.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 11px; background: transparent;")
            self._status_lbl.setText("已连接")
            self._status_lbl.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 11px; font-weight: 600; background: transparent;")
            self._connect_btn.setText("断开")
            self._connect_btn.setStyleSheet("font-size: 12px;")
        else:
            self._dot_lbl.setStyleSheet(f"color: {Colors.TEXT_TERTIARY}; font-size: 11px; background: transparent;")
            short = detail[:15] if detail else "未连接"
            self._status_lbl.setText(short)
            self._status_lbl.setStyleSheet(f"color: {Colors.TEXT_TERTIARY}; font-size: 11px; background: transparent;")
            self._connect_btn.setText("连接")
            self._connect_btn.setStyleSheet("font-size: 12px;")


class InstrumentSettingsDialog(QDialog):
    """仪器设置对话框。"""

    signal_reconnect = pyqtSignal(str)
    signal_disconnect = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mgr = InstrumentManager.instance()
        self._rows: dict[str, _InstrumentRow] = {}
        self.setWindowTitle("仪器设置")
        self.setMinimumSize(720, 320)
        self.resize(800, 360)
        self._setup_style()
        self._build_ui()
        self._load_config()

    def _setup_style(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.WINDOW_BG};
            }}
            QRadioButton {{
                font-size: 12px;
            }}
            QLineEdit {{
                font-size: 12px;
            }}
            QComboBox {{
                font-size: 12px;
            }}
        """)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 20, 28, 20)
        root.setSpacing(ROW_SPACING)

        title = _label("仪器连接设置", 16, bold=True)
        root.addWidget(title)
        root.addSpacing(4)

        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(ROW_SPACING)

        self._dmm_row = _InstrumentRow("34970A", "34970A 数字万用表", ["USB", "GPIB"])
        self._dmm_row.signal_connect.connect(self.signal_reconnect.emit)
        self._dmm_row.signal_disconnect.connect(self.signal_disconnect.emit)
        cards_layout.addWidget(self._dmm_row, 1)
        self._rows["34970A"] = self._dmm_row

        self._ps_row = _InstrumentRow("IT6382", "IT6382 程控电源", ["USB", "GPIB"])
        self._ps_row.signal_connect.connect(self.signal_reconnect.emit)
        self._ps_row.signal_disconnect.connect(self.signal_disconnect.emit)
        cards_layout.addWidget(self._ps_row, 1)
        self._rows["IT6382"] = self._ps_row

        self._relay_row = _InstrumentRow("Relayboard", "Relayboard", ["USB"])
        self._relay_row.signal_connect.connect(self.signal_reconnect.emit)
        self._relay_row.signal_disconnect.connect(self.signal_disconnect.emit)
        cards_layout.addWidget(self._relay_row, 1)
        self._rows["Relayboard"] = self._relay_row

        root.addLayout(cards_layout)
        root.addSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = PrimaryPushButton(FluentIcon.SAVE, "保存并关闭")
        save_btn.setFixedWidth(140)
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(save_btn)
        root.addLayout(btn_row)

    def _load_config(self):
        cfg = self._mgr.config

        dmm_mode = cfg.get("dmm_mode", "usb")
        self._dmm_row.set_mode(dmm_mode)
        if dmm_mode == "usb":
            self._dmm_row.set_port_value(cfg.get("dmm_port", ""))
        else:
            self._dmm_row.set_port_value(cfg.get("dmm_gpib", "11"))

        ps_mode = cfg.get("ps_mode", "gpib")
        self._ps_row.set_mode(ps_mode)
        if ps_mode == "usb":
            self._ps_row.set_port_value(cfg.get("ps_usb_port", ""))
        else:
            self._ps_row.set_port_value(cfg.get("ps_port", "8"))

        self._relay_row.set_port_value(cfg.get("relay_port", ""))

    def _on_save(self):
        dmm_mode = self._dmm_row.get_mode()
        dmm_port = self._dmm_row.get_port_value()
        ps_mode = self._ps_row.get_mode()
        ps_port = self._ps_row.get_port_value()
        self._mgr.update_config(
            dmm_mode=dmm_mode,
            dmm_port=dmm_port if dmm_mode == "usb" else self._mgr.config.get("dmm_port", ""),
            dmm_gpib=dmm_port if dmm_mode == "gpib" else self._mgr.config.get("dmm_gpib", "11"),
            ps_mode=ps_mode,
            ps_usb_port=ps_port if ps_mode == "usb" else self._mgr.config.get("ps_usb_port", ""),
            ps_port=ps_port if ps_mode == "gpib" else self._mgr.config.get("ps_port", "8"),
            relay_port=self._relay_row.get_port_value(),
        )
        self.close()

    def set_device_status(self, device_name: str, connected: bool, detail: str):
        row = self._rows.get(device_name)
        if row:
            row.set_status(connected, detail)
