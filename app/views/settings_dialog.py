"""设置对话框 — macOS 风格：左侧标签栏 + 右侧滚动卡片，滚动联动高亮。"""

import os
import serial.tools.list_ports
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QLabel,
    QFrame,
    QSizePolicy,
    QScrollArea,
    QFileDialog,
    QPushButton,
    QButtonGroup,
    QMessageBox,
)
from PyQt5.QtGui import QFont, QPixmap, QPainter, QColor, QBrush, QPen
from qfluentwidgets import (
    PrimaryPushButton,
    LineEdit,
    ComboBox,
    SwitchButton,
    FluentIcon,
    PasswordLineEdit,
    InfoBar,
    InfoBarIcon,
    InfoBarPosition,
)
from app.utils.logger import get_logger
from app.utils.config import load_config, save_config
from app.views.theme import Colors, FONT_FAMILY, BORDER_RADIUS

logger = get_logger("Settings")
from app.controllers.instrument_manager import InstrumentManager

# ═══════════════════════════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════════════════════════


def _list_serial_ports():
    return [p.device for p in serial.tools.list_ports.comports()]


def _font(size: int = 12, bold: bool = False) -> QFont:
    family = FONT_FAMILY.split(",")[0].strip('"')
    f = QFont(family, size)
    if bold:
        f.setBold(True)
    return f


# ═══════════════════════════════════════════════════════════════════════════
#  设置卡片基类
# ═══════════════════════════════════════════════════════════════════════════


class _SettingCard(QFrame):
    """基础设置卡片：左侧图标 → 标题+描述 → 右侧控件。"""

    def __init__(self, icon, title: str, content: str = "", parent=None):
        super().__init__(parent)
        self._build(icon, title, content)

    def _build(self, icon, title, content):
        self.setFixedHeight(60)
        self.setStyleSheet(f"""
            _SettingCard {{
                background-color: white;
                border: 1px solid #E5E5EA;
                border-radius: {BORDER_RADIUS}px;
            }}
            _SettingCard:hover {{ border-color: {Colors.PRIMARY}; }}
        """)
        row = QHBoxLayout(self)
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(12)

        # 图标
        icon_lbl = QLabel()
        if isinstance(icon, FluentIcon):
            icon_lbl.setPixmap(icon.icon().pixmap(22, 22))
        icon_lbl.setFixedSize(36, 36)
        icon_lbl.setAlignment(Qt.AlignCenter)
        row.addWidget(icon_lbl)

        # 文字
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        self._title_lbl = QLabel(title)
        self._title_lbl.setFont(_font(13, bold=True))
        self._title_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; background: transparent; border: none;"
        )
        text_col.addWidget(self._title_lbl)

        self._content_lbl = QLabel(content)
        self._content_lbl.setFont(_font(11))
        self._content_lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; background: transparent; border: none;"
        )
        self._content_lbl.setWordWrap(True)
        text_col.addWidget(self._content_lbl)
        row.addLayout(text_col, 1)

        self._right_layout = QHBoxLayout()
        self._right_layout.setSpacing(8)
        row.addLayout(self._right_layout)

    def set_content(self, text: str):
        self._content_lbl.setText(text)


class _PushSettingCard(_SettingCard):
    """可点击选择路径的卡片。"""

    clicked = pyqtSignal()

    def __init__(self, icon, title: str, content: str = "", parent=None):
        super().__init__(icon, title, content, parent)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        self.clicked.emit()


class _SwitchCard(_SettingCard):
    """带 SwitchButton 的卡片。"""

    def __init__(self, icon, title: str, content: str = "", parent=None):
        super().__init__(icon, title, content, parent)
        self._switch = SwitchButton()
        self._right_layout.addWidget(self._switch)

    @property
    def switch(self):
        return self._switch


class _ComboCard(_SettingCard):
    """带 ComboBox 的卡片。"""

    def __init__(self, icon, title: str, content: str = "", parent=None):
        super().__init__(icon, title, content, parent)
        self._combo = ComboBox()
        self._combo.setMinimumWidth(220)
        self._right_layout.addWidget(self._combo)

    @property
    def combo(self):
        return self._combo


class _LineEditCard(_SettingCard):
    """带 LineEdit 的卡片。"""

    def __init__(self, icon, title: str, content: str = "", parent=None):
        super().__init__(icon, title, content, parent)
        self._edit = LineEdit()
        self._edit.setMinimumWidth(220)
        self._edit.setClearButtonEnabled(True)
        self._right_layout.addWidget(self._edit)

    @property
    def edit(self):
        return self._edit


# ═══════════════════════════════════════════════════════════════════════════
#  多通道配置卡片
# ═══════════════════════════════════════════════════════════════════════════

INSTRUMENT_OPTIONS = ["无仪器", "34970A", "IT6382", "Relayboard"]


class _ChannelConfigCard(QFrame):
    """单通道配置卡片：Location ID + 仪器绑定 + 状态。"""

    # 通知其他通道：仪器已被选 (channel_index, instrument_name)
    instrument_changed = pyqtSignal(int, str)

    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self._index = index
        self._build()

    def _build(self):
        self.setStyleSheet(f"""
            _ChannelConfigCard {{
                background-color: white;
                border: 1px solid #E5E5EA;
                border-radius: {BORDER_RADIUS}px;
            }}
            _ChannelConfigCard:hover {{ border-color: {Colors.PRIMARY}; }}
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(8)

        # ── 标题行：通道名 + 状态 ──
        header = QHBoxLayout()
        header.setSpacing(8)

        self._name_lbl = QLabel(f"🔵 通道 {self._index + 1}")
        self._name_lbl.setFont(_font(14, bold=True))
        self._name_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; background: transparent; border: none;"
        )
        header.addWidget(self._name_lbl)

        header.addStretch()

        self._status_dot = QLabel("⚫")
        self._status_dot.setFont(_font(10))
        self._status_dot.setToolTip("通道状态")
        header.addWidget(self._status_dot)

        self._status_text = QLabel("未配置")
        self._status_text.setFont(_font(11))
        self._status_text.setStyleSheet(
            f"color: {Colors.TEXT_TERTIARY}; background: transparent; border: none;"
        )
        header.addWidget(self._status_text)

        outer.addLayout(header)

        # ── 内容行 ──
        body = QHBoxLayout()
        body.setSpacing(12)

        # DUT Location ID
        dut_label = QLabel("DUT")
        dut_label.setFont(_font(12))
        dut_label.setFixedWidth(32)
        dut_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; background: transparent; border: none;"
        )
        body.addWidget(dut_label)

        self._loc_edit = LineEdit()
        self._loc_edit.setPlaceholderText(f"Location ID (如 0x1420000{self._index})")
        self._loc_edit.setClearButtonEnabled(True)
        self._loc_edit.setMinimumWidth(180)
        body.addWidget(self._loc_edit, 1)

        # 仪器选择
        instr_label = QLabel("仪器")
        instr_label.setFont(_font(12))
        instr_label.setFixedWidth(28)
        instr_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; background: transparent; border: none;"
        )
        body.addWidget(instr_label)

        self._instr_combo = ComboBox()
        self._instr_combo.addItems(INSTRUMENT_OPTIONS)
        self._instr_combo.setCurrentIndex(0)
        self._instr_combo.setMinimumWidth(140)
        self._instr_combo.currentTextChanged.connect(self._on_instrument_changed)
        body.addWidget(self._instr_combo)

        outer.addLayout(body)

    def _on_instrument_changed(self, text: str):
        self.instrument_changed.emit(self._index, text)

    # ── 属性 ──

    @property
    def loc_edit(self) -> LineEdit:
        return self._loc_edit

    @property
    def instr_combo(self) -> ComboBox:
        return self._instr_combo

    @property
    def index(self) -> int:
        return self._index

    def get_location_id(self) -> str:
        return self._loc_edit.text().strip()

    def set_location_id(self, val: str):
        self._loc_edit.setText(val)

    def get_instrument(self) -> str:
        return self._instr_combo.currentText()

    def set_instrument(self, val: str):
        idx = self._instr_combo.findText(val)
        if idx >= 0:
            self._instr_combo.setCurrentIndex(idx)

    def set_status(self, connected: bool):
        if connected:
            self._status_dot.setText("🟢")
            self._status_text.setText("已连接")
            self._status_text.setStyleSheet(
                f"color: {Colors.SUCCESS}; font-weight: 600; background: transparent; border: none;"
            )
        else:
            self._status_dot.setText("⚫")
            self._status_text.setText("未连接")
            self._status_text.setStyleSheet(
                f"color: {Colors.TEXT_TERTIARY}; background: transparent; border: none;"
            )


# ═══════════════════════════════════════════════════════════════════════════
#  仪器卡片行
# ═══════════════════════════════════════════════════════════════════════════


class _InstrumentRow(QFrame):
    """单台仪器连接卡片。"""

    signal_connect = pyqtSignal(str)
    signal_disconnect = pyqtSignal(str)

    def __init__(
        self, device_id: str, display_name: str, port_types: list[str], parent=None
    ):
        super().__init__(parent)
        self._device_id = device_id
        self._port_types = port_types
        self._connected = False
        self._port_combo: ComboBox | None = None
        self._addr_input: LineEdit | None = None
        self._connect_btn: PrimaryPushButton | None = None
        self._dot_lbl: QLabel | None = None
        self._status_lbl: QLabel | None = None
        self._mode_radios: dict = {}
        self._build(display_name)

    def _build(self, display_name):
        self.setFrameShape(QFrame.NoFrame)
        self.setStyleSheet(f"""
            _InstrumentRow {{
                background-color: white;
                border: 1px solid #E5E5EA;
                border-radius: {BORDER_RADIUS}px;
            }}
            _InstrumentRow:hover {{ border-color: {Colors.PRIMARY}; }}
        """)

        row = QHBoxLayout(self)
        row.setContentsMargins(14, 8, 14, 8)
        row.setSpacing(12)

        name_lbl = QLabel(display_name)
        name_lbl.setFont(_font(13, bold=True))
        name_lbl.setFixedWidth(160)
        name_lbl.setStyleSheet(
            f"color: {Colors.TEXT_PRIMARY}; background: transparent;"
        )
        row.addWidget(name_lbl)

        has_usb = "USB" in self._port_types
        has_gpib = "GPIB" in self._port_types

        if len(self._port_types) > 1:
            from qfluentwidgets import RadioButton

            for pt in self._port_types:
                rb = RadioButton(pt)
                rb.setChecked(pt == "USB")
                rb.toggled.connect(self._make_handler(pt))
                self._mode_radios[pt] = rb
                row.addWidget(rb)
        else:
            mode_lbl = QLabel(self._port_types[0])
            mode_lbl.setFixedWidth(60)
            mode_lbl.setFont(_font(12))
            mode_lbl.setStyleSheet(
                f"color: {Colors.TEXT_SECONDARY}; background: transparent;"
            )
            row.addWidget(mode_lbl)

        row.addSpacing(8)

        self._port_combo = ComboBox()
        self._port_combo.setMinimumWidth(200)
        self._port_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        ports = _list_serial_ports()
        if ports:
            self._port_combo.addItems(ports)
        self._port_combo.setVisible(has_usb)
        row.addWidget(self._port_combo, 1)

        self._addr_input = LineEdit()
        self._addr_input.setMinimumWidth(100)
        self._addr_input.setPlaceholderText("GPIB 地址")
        self._addr_input.setVisible(has_gpib)
        row.addWidget(self._addr_input, 1)

        row.addStretch()

        self._connect_btn = PrimaryPushButton("连接")
        self._connect_btn.setFixedSize(80, 32)
        self._connect_btn.clicked.connect(self._on_connect)
        row.addWidget(self._connect_btn)

        self._dot_lbl = QLabel("●")
        self._dot_lbl.setFixedWidth(14)
        self._dot_lbl.setAlignment(Qt.AlignCenter)
        self._dot_lbl.setStyleSheet(
            f"color: {Colors.TEXT_TERTIARY}; background: transparent;"
        )
        row.addWidget(self._dot_lbl)

        self._status_lbl = QLabel("未连接")
        self._status_lbl.setFixedWidth(50)
        self._status_lbl.setFont(_font(11))
        self._status_lbl.setStyleSheet(
            f"color: {Colors.TEXT_TERTIARY}; background: transparent;"
        )
        row.addWidget(self._status_lbl)

    def _make_handler(self, mode: str):
        def handler(checked: bool):
            if checked:
                self._port_combo.setVisible(mode == "USB")
                self._addr_input.setVisible(mode == "GPIB")

        return handler

    def _on_connect(self):
        if self._connected:
            self.signal_disconnect.emit(self._device_id)
        else:
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
            self._dot_lbl.setStyleSheet(
                f"color: {Colors.SUCCESS}; background: transparent;"
            )
            self._status_lbl.setText("已连接")
            self._status_lbl.setStyleSheet(
                f"color: {Colors.SUCCESS}; font-weight: 600; background: transparent;"
            )
            self._connect_btn.setText("断开")
        else:
            self._dot_lbl.setStyleSheet(
                f"color: {Colors.TEXT_TERTIARY}; background: transparent;"
            )
            short = detail[:12] if detail else "未连接"
            self._status_lbl.setText(short)
            self._status_lbl.setStyleSheet(
                f"color: {Colors.TEXT_TERTIARY}; background: transparent;"
            )
            self._connect_btn.setText("连接")


# ═══════════════════════════════════════════════════════════════════════════
#  左侧标签按钮（可高亮）
# ═══════════════════════════════════════════════════════════════════════════


class _SidebarBtn(QPushButton):
    """左侧标签按钮 — 仿 macOS 设置侧栏。"""

    def __init__(self, icon: FluentIcon, text: str, parent=None):
        super().__init__(text, parent)  # 直接设 text
        self._active = False
        self._icon = icon
        self._text = text
        self.setFixedHeight(42)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(True)
        self._update_style()

    def set_active(self, active: bool):
        if self._active != active:
            self._active = active
            self.setChecked(active)
            self._update_style()

    def _update_style(self):
        if self._active:
            bg = "rgba(0,122,255,0.1)"
            clr = Colors.PRIMARY
            wt = "600"
        else:
            bg = "transparent"
            clr = Colors.TEXT_SECONDARY
            wt = "400"

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                color: {clr};
                font-weight: {wt};
                border: none;
                border-radius: 6px;
                text-align: left;
                padding-left: 12px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: rgba(0,0,0,0.05);
            }}
        """)


# ═══════════════════════════════════════════════════════════════════════════
#  设置对话框主类 — 左侧标签 + 右侧滚动
# ═══════════════════════════════════════════════════════════════════════════


class SettingsDialog(QDialog):
    """macOS 风格设置对话框：左侧标签栏 + 右侧滚动卡片，滚动联动高亮。"""

    signal_reconnect = pyqtSignal(str)
    signal_disconnect = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mgr = InstrumentManager.instance()
        self._rows: dict[str, _InstrumentRow] = {}
        self._system_config = load_config()
        self._original_config = dict(self._system_config)
        self._section_anchors: dict[str, QLabel] = {}  # 段名 → header QLabel
        self._sidebar_btns: dict[str, _SidebarBtn] = {}
        self._scroll_locked = False
        self._is_unlocked = False

        self.setWindowTitle("设置")
        self.resize(1050, 600)
        self.setMinimumSize(780, 600)
        self.setWindowModality(Qt.ApplicationModal)

        self._build_ui()
        self._build_all_cards()
        self._load_instrument_config()

        # 初始锁定所有编辑控件
        self._set_editing_enabled(False)

    # ── UI 构建 ────────────────────────────────────────────────────────

    def _build_ui(self):
        self.setStyleSheet(f"QDialog {{ background-color: {Colors.WINDOW_BG}; }}")

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 12, 20, 12)
        root.setSpacing(0)

        # 标题行：标题 + 密码
        title_row = QHBoxLayout()
        title = QLabel("设置")
        title.setFont(_font(18, bold=True))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; background: transparent;")
        title_row.addWidget(title)
        title_row.addStretch()

        self._pwd_edit = PasswordLineEdit()
        self._pwd_edit.setPlaceholderText("输入密码解锁编辑")
        self._pwd_edit.setFixedWidth(200)
        self._pwd_edit.textChanged.connect(self._on_password_changed)
        title_row.addWidget(self._pwd_edit)

        root.addLayout(title_row)
        root.addSpacing(12)

        # ── 左右结构 ──
        body = QHBoxLayout()
        body.setSpacing(0)

        # 左侧标签栏
        sidebar = QWidget()
        sidebar.setFixedWidth(160)
        sidebar.setStyleSheet(
            f"background-color: transparent; border-right: 1px solid {Colors.SEPARATOR};"
        )
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 8, 12, 8)
        sidebar_layout.setSpacing(4)

        icons = {
            "仪器设置": FluentIcon.DEVELOPER_TOOLS,
            "SFC 设置": FluentIcon.GLOBE,
            "串口设置": FluentIcon.LINK,
            "通用设置": FluentIcon.SETTING,
            "系统设置": FluentIcon.APPLICATION,
        }
        sidebar_names = ["仪器设置", "SFC 设置", "串口设置", "通用设置", "系统设置"]
        for name in sidebar_names:
            btn = _SidebarBtn(icons[name], name)
            btn.clicked.connect(self._make_scroll_handler(name))
            sidebar_layout.addWidget(btn)
            self._sidebar_btns[name] = btn
        sidebar_layout.addStretch()
        body.addWidget(sidebar)

        # 右侧滚动区域
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )
        self._scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self._content = QWidget()
        self._content.setStyleSheet("background: transparent;")
        self._card_layout = QVBoxLayout(self._content)
        self._card_layout.setContentsMargins(20, 4, 4, 16)
        self._card_layout.setSpacing(10)
        self._card_layout.addStretch()

        self._scroll.setWidget(self._content)
        body.addWidget(self._scroll, 1)
        root.addLayout(body, 1)

        # 底部保存按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._save_btn = PrimaryPushButton(FluentIcon.SAVE, "保存并关闭")
        self._save_btn.setFixedWidth(140)
        self._save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(self._save_btn)
        root.addLayout(btn_row)

    def _add_section_header(self, text: str):
        """在卡片列表中添加分段标题，保存 label 引用用于后续计算锚点。"""
        if self._card_layout.count():
            last = self._card_layout.takeAt(self._card_layout.count() - 1)
            if last.spacerItem():
                del last

        lbl = QLabel(text)
        lbl.setFont(_font(11, bold=True))
        lbl.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY}; background: transparent; "
            f"text-transform: uppercase; letter-spacing: 0.5px; padding: 0 2px;"
        )
        self._card_layout.addWidget(lbl)
        self._card_layout.addStretch()
        self._section_anchors[text] = lbl  # 存 QLabel 引用

    def _make_scroll_handler(self, section: str):
        """返回一个闭包：点击侧栏按钮 → 滚动到对应段。"""

        def handler():
            self._scroll_locked = True
            lbl = self._section_anchors.get(section)
            y = lbl.pos().y() if lbl else 0
            self._scroll.verticalScrollBar().setValue(max(0, y))
            for name, btn in self._sidebar_btns.items():
                btn.set_active(name == section)
            from PyQt5.QtCore import QTimer

            QTimer.singleShot(300, lambda: setattr(self, "_scroll_locked", False))

        return handler

    def _on_scroll(self, value: int):
        """滚动时自动高亮当前可见段。"""
        if self._scroll_locked:
            return
        current = None
        for name in ["仪器设置", "SFC 设置", "串口设置", "通用设置", "系统设置"]:
            lbl = self._section_anchors.get(name)
            if lbl is None:
                continue
            y = lbl.pos().y()
            if value >= y - 30:
                current = name
        if current:
            for name, btn in self._sidebar_btns.items():
                btn.set_active(name == current)

    # ── 卡片构建 ────────────────────────────────────────────────────────

    def _build_all_cards(self):
        self._build_instrument_cards()
        self._build_sfc_cards()
        self._build_serial_cards()
        self._build_general_cards()
        self._build_system_cards()

    def _build_instrument_cards(self):
        self._add_section_header("仪器设置")

        self._dmm_row = _InstrumentRow("34970A", "34970A 数字万用表", ["USB", "GPIB"])
        self._dmm_row.signal_connect.connect(self.signal_reconnect.emit)
        self._dmm_row.signal_disconnect.connect(self.signal_disconnect.emit)
        self._add_card(self._dmm_row)
        self._rows["34970A"] = self._dmm_row

        self._ps_row = _InstrumentRow("IT6382", "IT6382 程控电源", ["USB", "GPIB"])
        self._ps_row.signal_connect.connect(self.signal_reconnect.emit)
        self._ps_row.signal_disconnect.connect(self.signal_disconnect.emit)
        self._add_card(self._ps_row)
        self._rows["IT6382"] = self._ps_row

        self._relay_row = _InstrumentRow("Relayboard", "Relayboard 继电器板", ["USB"])
        self._relay_row.signal_connect.connect(self.signal_reconnect.emit)
        self._relay_row.signal_disconnect.connect(self.signal_disconnect.emit)
        self._add_card(self._relay_row)
        self._rows["Relayboard"] = self._relay_row

        # 刷新端口按钮
        refresh_row = QHBoxLayout()
        refresh_row.addStretch()
        refresh_btn = PrimaryPushButton("刷新串口列表")
        refresh_btn.setFixedWidth(130)
        refresh_btn.clicked.connect(self._refresh_ports)
        refresh_row.addWidget(refresh_btn)
        self._add_layout(refresh_row)

        self._card_layout.addSpacing(20)

    def _build_sfc_cards(self):
        self._add_section_header("SFC 设置")

        self._sfc_url_card = _LineEditCard(
            FluentIcon.CLOUD, "SFC Server URL", "SFC 服务器的完整地址"
        )
        self._sfc_url_card.edit.setPlaceholderText(
            "http://10.53.7.7:8081/Command_Code.asmx/command_code_for_webservice?"
        )
        stored = self._system_config.get("sfc_url", "")
        if stored:
            self._sfc_url_card.edit.setText(stored)
        self._add_card(self._sfc_url_card)

        self._sfc_online_card = _SwitchCard(
            FluentIcon.LINK,
            "UOP 在线模式",
            "开启后向 SFC 系统实时上报测试结果；关闭则离线运行",
        )
        self._sfc_online_card.switch.setChecked(
            self._system_config.get("sfc_online", False)
        )
        self._add_card(self._sfc_online_card)

        self._sfc_vip_card = _LineEditCard(
            FluentIcon.WIFI, "VIP 地址 (Terminal IP)", "SFC 系统绑定的终端 IP 地址"
        )
        self._sfc_vip_card.edit.setPlaceholderText("172.32.16.78")
        stored_vip = self._system_config.get("sfc_vip", "")
        if stored_vip:
            self._sfc_vip_card.edit.setText(stored_vip)
        self._add_card(self._sfc_vip_card)

        self._card_layout.addSpacing(20)

    def _build_serial_cards(self):
        self._add_section_header("串口设置")

        self._baud_card = _ComboCard(
            FluentIcon.SPEED_HIGH, "DUT 波特率", "与 DUT 串口通信的速率"
        )
        self._baud_card.combo.addItems(["9600", "115200", "921600"])
        self._baud_card.combo.setCurrentText(
            str(self._system_config.get("dut_baud_rate", 921600))
        )
        self._add_card(self._baud_card)

        self._location_id_card = _LineEditCard(
            FluentIcon.PIN,
            "DUT Location ID",
            "USB 串口 Location ID，用于自动模式识别 DUT（可用 system_profiler SPUSBDataType 查看）",
        )
        stored_loc = self._system_config.get("dut_location_id", "")
        if stored_loc:
            self._location_id_card.edit.setText(stored_loc)
        self._location_id_card.edit.setPlaceholderText("如 0x14200000")
        self._add_card(self._location_id_card)

        self._auto_test_card = _SwitchCard(
            FluentIcon.ROBOT,
            "自动测试模式",
            "开启后监控 DUT 串口，检测到连接自动开始测试（无需点 Start）",
        )
        self._auto_test_card.switch.setChecked(
            self._system_config.get("auto_test_mode", False)
        )
        self._add_card(self._auto_test_card)

        # ── 多通道测试 ──
        self._multi_channel_card = _SwitchCard(
            FluentIcon.IOT,
            "多通道测试模式",
            "开启后同时测试多个 DUT，每个通道独立串口（需重启软件生效）",
        )
        self._multi_channel_card.switch.setChecked(
            self._system_config.get("multi_channel_mode", False)
        )
        self._multi_channel_card.switch.checkedChanged.connect(self._on_multi_channel_toggled)
        self._add_card(self._multi_channel_card)

        # DUT 设备列表
        self._dut_list_card = _PushSettingCard(
            FluentIcon.INFO,
            "可用 DUT 设备",
            "点击查看当前连接的 DUT 设备及其 Location ID",
        )
        self._dut_list_card.clicked.connect(self._on_show_dut_list)
        self._add_card(self._dut_list_card)

        # 通道数量
        self._channel_count_card = _ComboCard(
            FluentIcon.MENU,
            "通道数量",
            "同时测试的 DUT 数量",
        )
        self._channel_count_card.combo.addItems([str(i) for i in range(1, 9)])
        self._channel_count_card.combo.setCurrentText(
            str(self._system_config.get("channel_count", 4))
        )
        self._channel_count_card.combo.currentTextChanged.connect(self._on_channel_count_changed)
        self._add_card(self._channel_count_card)

        # 每个通道的配置卡片（Location ID + 仪器选择）
        self._channel_cards: list[_ChannelConfigCard] = []
        channel_ids = self._system_config.get("channel_location_ids", ["", "", "", ""])
        channel_instrs = self._system_config.get("channel_instruments", ["", "", "", ""])
        for i in range(8):
            card = _ChannelConfigCard(i)
            if i < len(channel_ids):
                card.set_location_id(channel_ids[i])
            if i < len(channel_instrs) and channel_instrs[i]:
                card.set_instrument(channel_instrs[i])
            # 仪器互斥：同一仪器只能选一次
            card.instrument_changed.connect(self._on_channel_instrument_changed)
            self._add_card(card)
            self._channel_cards.append(card)

        # 初始同步可见性
        self._sync_channel_loc_visibility()

        self._card_layout.addSpacing(20)

    def _build_general_cards(self):
        self._add_section_header("通用设置")

        self._fail_stop_card = _SwitchCard(
            FluentIcon.CANCEL_MEDIUM,
            "Fail 时停止测试",
            "测试项失败后是否继续执行后续测试",
        )
        self._fail_stop_card.switch.setChecked(
            self._system_config.get("fail_stop_test", True)
        )
        self._add_card(self._fail_stop_card)

        self._log_path_card = _PushSettingCard(
            FluentIcon.FOLDER,
            "日志保存路径",
            os.path.expanduser(
                self._system_config.get("log_path", "~/Documents/SpartaLog/TopLevelLog")
            ),
        )
        self._log_path_card.clicked.connect(self._on_select_log_path)
        self._add_card(self._log_path_card)

        self._card_layout.addSpacing(20)

    def _build_system_cards(self):
        self._add_section_header("系统设置")

        self._auto_scroll_card = _SwitchCard(
            FluentIcon.SCROLL,
            "自动滚动日志",
            "测试运行时日志面板自动跟随最新输出",
        )
        self._auto_scroll_card.switch.setChecked(
            self._system_config.get("auto_scroll_log", True)
        )
        self._add_card(self._auto_scroll_card)

        self._log_retention_card = _ComboCard(
            FluentIcon.HISTORY, "日志保留天数", "超过天数的日志文件自动清理"
        )
        self._log_retention_card.combo.addItems(["30", "60", "90", "180", "365"])
        self._log_retention_card.combo.setCurrentText(
            str(self._system_config.get("log_retention_days", 90))
        )
        self._add_card(self._log_retention_card)

        self._card_layout.addStretch()

    def _add_card(self, card: QWidget):
        """插入到末尾 stretch 之前。"""
        if self._card_layout.count():
            last = self._card_layout.takeAt(self._card_layout.count() - 1)
            self._card_layout.addWidget(card)
            self._card_layout.addItem(last)
        else:
            self._card_layout.addWidget(card)

    def _add_layout(self, layout):
        if self._card_layout.count():
            last = self._card_layout.takeAt(self._card_layout.count() - 1)
            self._card_layout.addLayout(layout)
            self._card_layout.addItem(last)
        else:
            self._card_layout.addLayout(layout)

    def _refresh_ports(self):
        ports = _list_serial_ports()
        for row in self._rows.values():
            if row._port_combo and row._port_combo.isVisible():
                current = row._port_combo.currentText()
                row._port_combo.clear()
                row._port_combo.addItems(ports)
                idx = row._port_combo.findText(current)
                if idx >= 0:
                    row._port_combo.setCurrentIndex(idx)

    def _on_show_dut_list(self):
        """展示当前可用的 DUT 设备及其 Location ID。"""
        from app.models.device import list_dut_devices
        devs = list_dut_devices()
        if devs:
            lines = ["当前连接的 DUT 设备:\n"]
            for i, d in enumerate(devs, 1):
                lines.append(f"  CH{i}: Location ID = {d['location_id']}  ({d['device']})")
            lines.append("\n将对应的 Location ID 填入下方通道配置中即可。")
            QMessageBox.information(self, "可用 DUT 设备", "\n".join(lines))
        else:
            QMessageBox.information(self, "可用 DUT 设备", "未检测到 DUT 串口设备")

    def _on_select_log_path(self):
        current = self._log_path_card._content_lbl.text()
        folder = QFileDialog.getExistingDirectory(self, "选择日志保存路径", current)
        if folder:
            self._log_path_card.set_content(folder)
            self._system_config["log_path"] = folder

    # ── 多通道回调 ─────────────────────────────────────────────────

    def _on_multi_channel_toggled(self, checked: bool):
        self._sync_channel_loc_visibility()

    def _on_channel_count_changed(self, text: str):
        self._sync_channel_loc_visibility()

    def _on_channel_instrument_changed(self, channel_index: int, instrument: str):
        """仪器互斥：同一仪器不能同时分配给多个通道。"""
        if instrument == "无仪器":
            return
        # 把其他通道的同一仪器清除
        for i, card in enumerate(self._channel_cards):
            if i != channel_index and card.get_instrument() == instrument:
                card.set_instrument("无仪器")

    def _sync_channel_loc_visibility(self):
        """根据 multi_channel_mode 和 channel_count 显示/隐藏通道配置卡片。"""
        multi = self._multi_channel_card.switch.isChecked()
        count = int(self._channel_count_card.combo.currentText()) if multi else 0
        for i, card in enumerate(self._channel_cards):
            card.setVisible(multi and i < count)

    # ── 配置加载/保存 ──────────────────────────────────────────────────

    def _load_instrument_config(self):
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

    # ── 密码解锁 ──────────────────────────────────────────────────────

    def _on_password_changed(self, text: str):
        """输入正确密码后解锁所有编辑控件。"""
        if text == "123":
            self._is_unlocked = True
            self._pwd_edit.setVisible(False)
            self._set_editing_enabled(True)
            self._show_info_bar("已解锁", "设置编辑已启用")

    def _set_editing_enabled(self, enabled: bool):
        """启用/禁用所有可编辑控件。"""
        self._save_btn.setEnabled(enabled)
        # 仪器行
        for row in self._rows.values():
            if row._port_combo:
                row._port_combo.setEnabled(enabled)
            if row._addr_input:
                row._addr_input.setEnabled(enabled)
            if row._connect_btn:
                row._connect_btn.setEnabled(enabled)
            for rb in row._mode_radios.values():
                rb.setEnabled(enabled)
        # SFC 设置
        self._sfc_url_card.edit.setEnabled(enabled)
        self._sfc_online_card.switch.setEnabled(enabled)
        self._sfc_vip_card.edit.setEnabled(enabled)
        # 串口设置
        self._baud_card.combo.setEnabled(enabled)
        self._location_id_card.edit.setEnabled(enabled)
        self._auto_test_card.switch.setEnabled(enabled)
        # 多通道设置
        self._multi_channel_card.switch.setEnabled(enabled)
        self._channel_count_card.combo.setEnabled(enabled)
        for card in self._channel_cards:
            card.loc_edit.setEnabled(enabled)
            card.instr_combo.setEnabled(enabled)
        # 通用设置
        self._fail_stop_card.switch.setEnabled(enabled)
        # 系统设置
        self._auto_scroll_card.switch.setEnabled(enabled)
        self._log_retention_card.combo.setEnabled(enabled)

    def _show_info_bar(self, title: str, content: str):
        """显示顶部提示条。"""
        try:
            _info = InfoBar(
                icon=InfoBarIcon.SUCCESS,
                title=title,
                content=content,
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=2000,
                parent=self,
            )
            _info.show()
        except Exception:
            pass

    def _on_save(self):
        if not self._is_unlocked:
            return

        dmm_mode = self._dmm_row.get_mode()
        dmm_port = self._dmm_row.get_port_value()
        ps_mode = self._ps_row.get_mode()
        ps_port = self._ps_row.get_port_value()
        self._mgr.update_config(
            dmm_mode=dmm_mode,
            dmm_port=dmm_port
            if dmm_mode == "usb"
            else self._mgr.config.get("dmm_port", ""),
            dmm_gpib=dmm_port
            if dmm_mode == "gpib"
            else self._mgr.config.get("dmm_gpib", "11"),
            ps_mode=ps_mode,
            ps_usb_port=ps_port
            if ps_mode == "usb"
            else self._mgr.config.get("ps_usb_port", ""),
            ps_port=ps_port
            if ps_mode == "gpib"
            else self._mgr.config.get("ps_port", "8"),
            relay_port=self._relay_row.get_port_value(),
        )

        self._system_config["sfc_url"] = self._sfc_url_card.edit.text().strip()
        self._system_config["sfc_online"] = self._sfc_online_card.switch.isChecked()
        self._system_config["sfc_vip"] = self._sfc_vip_card.edit.text().strip()
        self._system_config["dut_baud_rate"] = int(self._baud_card.combo.currentText())
        self._system_config["dut_location_id"] = self._location_id_card.edit.text().strip()
        self._system_config["auto_test_mode"] = self._auto_test_card.switch.isChecked()
        self._system_config["multi_channel_mode"] = self._multi_channel_card.switch.isChecked()
        self._system_config["channel_count"] = int(self._channel_count_card.combo.currentText())
        loc_ids = [c.get_location_id() for c in self._channel_cards[:8]]
        instr_ids = [c.get_instrument() if c.get_instrument() != "无仪器" else "" for c in self._channel_cards[:8]]
        self._system_config["channel_location_ids"] = loc_ids
        self._system_config["channel_instruments"] = instr_ids
        self._system_config["fail_stop_test"] = self._fail_stop_card.switch.isChecked()
        self._system_config["auto_scroll_log"] = (
            self._auto_scroll_card.switch.isChecked()
        )
        self._system_config["log_retention_days"] = int(
            self._log_retention_card.combo.currentText()
        )
        save_config(self._system_config)

        # 对比原始配置，有变更才提示重启
        if self._system_config != self._original_config:
            import sys as _sys, os as _os

            reply = QMessageBox.question(
                self, "重启确认",
                "设置已变更，重启软件后生效。",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes,
            )
            self.close()
            if reply == QMessageBox.Yes:
                python = _sys.executable
                _os.execl(python, python, *_sys.argv)
        else:
            self.close()

    def set_device_status(self, device_name: str, connected: bool, detail: str):
        row = self._rows.get(device_name)
        if row:
            row.set_status(connected, detail)

    def showEvent(self, event):
        super().showEvent(event)
        # 每次打开都重新锁定，必须输密码
        self._is_unlocked = False
        self._pwd_edit.setVisible(True)
        self._pwd_edit.clear()
        self._pwd_edit.setFocus()
        self._set_editing_enabled(False)
        # 默认高亮第一段
        if self._sidebar_btns:
            first = list(self._sidebar_btns.keys())[0]
            self._sidebar_btns[first].set_active(True)
        # 从 InstrumentManager 同步当前仪器状态（Dialog 懒创建，之前的信号已丢失）
        self._sync_instrument_status()
        # 快照当前配置，用于保存时对比是否有变更
        self._original_config = dict(self._system_config)

    def _sync_instrument_status(self):
        """从 InstrumentManager 拉取当前连接状态更新 UI。"""
        mgr = InstrumentManager.instance()
        for device_id, row in self._rows.items():
            if device_id == "34970A":
                connected = mgr.dmm_connected
            elif device_id == "IT6382":
                connected = mgr.ps_connected
            elif device_id == "Relayboard":
                connected = mgr.relay_connected
            else:
                continue
            detail = "已连接" if connected else "未连接"
            row.set_status(connected, detail)
