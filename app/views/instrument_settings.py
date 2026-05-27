"""仪器设置对话框 — QFluentWidgets 风格，Card 分组 + VBoxLayout 间距控制。"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QWidget, QApplication,
)
from PyQt5.QtCore import Qt, pyqtSignal
from qfluentwidgets import (
    CardWidget, PushButton, PrimaryPushButton, LineEdit, ComboBox,
    TitleLabel, SubtitleLabel, BodyLabel, StrongBodyLabel, CaptionLabel,
    VBoxLayout, isDarkTheme, FluentIcon,
)
from app.controllers.instrument_manager import InstrumentManager


FLUENT_H_MARGIN = 36   # Fluent Design 标准水平边距
FLUENT_V_MARGIN = 16   # 垂直边距
CARD_PADDING    = 20   # 卡片内部边距
SECTION_GAP     = 16   # 组间间距
ELEMENT_GAP     = 12   # 元素间距
ROW_GAP         = 8    # 行内间距
STATUS_DOT_SIZE = 10   # 状态圆点直径
LINEEDIT_WIDTH  = 260  # LineEdit 固定宽度
LINEEDIT_HEIGHT = 33   # LineEdit Fluent 标准高度
BUTTON_HEIGHT   = 32   # 按钮 Fluent 标准高度


class _InstrumentCard(CardWidget):
    """单台仪器卡片：状态圆点 + 名称 + IDN + 端口输入 + 重连按钮。"""

    signal_reconnect = pyqtSignal(str)

    def __init__(self, device_name: str, icon_char: str, parent=None):
        super().__init__(parent)
        self._device_name = device_name
        self._connected = False
        self._port_inputs: dict[str, QLineEdit] = {}
        self._port_rows: dict[str, QHBoxLayout] = {}
        self._mode_combo: ComboBox | None = None
        self._mode_map: dict[str, str] = {}  # mode_value → port_key

        self._setup_style()
        self._build(icon_char)

    def _setup_style(self):
        dark = isDarkTheme()
        self.setMinimumWidth(400)
        if dark:
            self.setStyleSheet("""
                CardWidget {
                    background-color: rgba(255, 255, 255, 0.05);
                    border: 1px solid rgba(255, 255, 255, 0.08);
                    border-radius: 8px;
                }
            """)
        else:
            self.setStyleSheet("""
                CardWidget {
                    background-color: rgba(255, 255, 255, 0.85);
                    border: 1px solid rgba(0, 0, 0, 0.06);
                    border-radius: 8px;
                }
            """)

    def _build(self, icon_char: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(CARD_PADDING, CARD_PADDING, CARD_PADDING, CARD_PADDING)
        root.setSpacing(ROW_GAP)

        # ── 标题行：图标 + 名称 + 状态点 + 状态文字 ──
        header = QHBoxLayout()
        header.setSpacing(ELEMENT_GAP)

        icon_lbl = QLabel(icon_char)
        icon_lbl.setFixedSize(28, 28)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(self._icon_style())
        header.addWidget(icon_lbl)

        name_lbl = StrongBodyLabel(self._device_name)
        header.addWidget(name_lbl)

        header.addStretch()

        self._dot = QLabel()
        self._dot.setFixedSize(STATUS_DOT_SIZE, STATUS_DOT_SIZE)
        self._dot.setStyleSheet(self._dot_style(False))
        header.addWidget(self._dot)

        self._status_label = BodyLabel("未连接")
        dark = isDarkTheme()
        self._status_label.setStyleSheet(
            f"color: {'#888888' if dark else '#999999'};"
        )
        header.addWidget(self._status_label)

        root.addLayout(header)

        # ── IDN 行 ──
        self._idn_label = CaptionLabel("等待检测…")
        dark2 = isDarkTheme()
        self._idn_label.setStyleSheet(
            f"color: {'#666666' if dark2 else '#AAAAAA'}; padding-left: 36px;"
        )
        root.addWidget(self._idn_label)

        # ── 端口输入行（由子类通过 add_port_row 添加） ──
        self._port_container = QVBoxLayout()
        self._port_container.setSpacing(ROW_GAP)
        root.addLayout(self._port_container)

        # ── 重连按钮 ──
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(0, 4, 0, 0)
        btn_row.addSpacing(36)
        reconnect_btn = PushButton(FluentIcon.SYNC, "  重新连接")
        reconnect_btn.setFixedHeight(BUTTON_HEIGHT)
        reconnect_btn.setToolTip(f"重新检测 {self._device_name} 连接")
        reconnect_btn.clicked.connect(lambda: self.signal_reconnect.emit(self._device_name))
        btn_row.addWidget(reconnect_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

    def add_port_row(self, config_key: str, label_text: str, default_val: str = ""):
        """添加一行 Label + QFluent LineEdit。"""
        row = QHBoxLayout()
        row.setSpacing(ROW_GAP)

        lbl = BodyLabel(label_text)
        lbl.setFixedWidth(80)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(lbl)

        inp = LineEdit()
        inp.setText(default_val)
        inp.setFixedWidth(LINEEDIT_WIDTH)
        inp.setFixedHeight(LINEEDIT_HEIGHT)
        inp.setClearButtonEnabled(True)
        inp.setToolTip(f"设置 {label_text}")
        row.addWidget(inp)

        row.addStretch()
        self._port_inputs[config_key] = inp
        self._port_rows[config_key] = row
        self._port_container.addLayout(row)

    def add_mode_selector(self, config_key: str, modes: list[tuple[str, str, str]]):
        """在端口行上方添加连接方式切换 ComboBox。

        modes 格式: [(mode_value, mode_label, port_key), ...]
        每个 mode 对应一个已通过 add_port_row 添加的端口行，
        切换时自动显示/隐藏对应的端口行。
        """
        mode_row = QHBoxLayout()
        mode_row.setSpacing(ROW_GAP)

        lbl = BodyLabel("连接方式")
        lbl.setFixedWidth(80)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        mode_row.addWidget(lbl)

        combo = ComboBox()
        combo.setFixedWidth(140)
        combo.setFixedHeight(LINEEDIT_HEIGHT)
        self._mode_combo = combo

        for val, label, _ in modes:
            combo.addItem(label, val)
        combo.currentIndexChanged.connect(lambda _: self._on_mode_changed())

        mode_row.addWidget(combo)
        mode_row.addStretch()
        self._port_container.addLayout(mode_row)

        self._mode_map = {val: port_key for val, _, port_key in modes}

    def _on_mode_changed(self):
        """根据当前 ComboBox 选择显示/隐藏对应端口行。"""
        current = self._mode_combo.currentData()
        for mode_val, port_key in self._mode_map.items():
            row = self._port_rows.get(port_key)
            if row is None:
                continue
            visible = (mode_val == current)
            for j in range(row.count()):
                w = row.itemAt(j)
                if w and w.widget():
                    w.widget().setVisible(visible)

    # ── 状态更新 ──

    def set_status(self, connected: bool, detail: str):
        self._connected = connected
        self._dot.setStyleSheet(self._dot_style(connected))

        dark = isDarkTheme()
        if connected:
            self._status_label.setText("已连接")
            self._status_label.setStyleSheet(
                f"color: {'#4caf50' if dark else '#2e7d32'}; font-weight: 600;"
            )
        else:
            self._status_label.setText(detail)
            self._status_label.setStyleSheet(
                f"color: {'#888888' if dark else '#999999'};"
            )

        self._idn_label.setText(detail if connected else f"信息: {detail}")

    # ── 数据存取 ──

    def get_port_values(self) -> dict[str, str]:
        vals = {k: v.text().strip() for k, v in self._port_inputs.items()}
        if self._mode_combo is not None:
            vals["dmm_mode"] = self._mode_combo.currentData()
        return vals

    def set_port_value(self, key: str, value: str):
        if key in self._port_inputs:
            self._port_inputs[key].setText(value)
        if key == "dmm_mode" and self._mode_combo is not None:
            idx = self._mode_combo.findData(value)
            if idx >= 0:
                self._mode_combo.setCurrentIndex(idx)
                self._on_mode_changed()

    # ── 样式 ──

    def _dot_style(self, connected: bool) -> str:
        color = "#4caf50" if connected else "#cccccc"
        return f"""
            background-color: {color};
            border-radius: {STATUS_DOT_SIZE // 2}px;
        """

    def _icon_style(self) -> str:
        return """
            font-size: 18px;
            border: none;
            background: transparent;
        """


class InstrumentSettingsDialog(QDialog):
    """仪器设置对话框 — Fluent Design 风格。"""

    signal_reconnect = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mgr = InstrumentManager.instance()
        self._cards: dict[str, _InstrumentCard] = {}

        self.setWindowTitle("仪器设置")
        self.setMinimumWidth(520)
        self.setModal(True)

        self._build_ui()
        self._load_config()
        self._connect_signals()

    def _build_ui(self):
        self._setup_window_style()

        root = VBoxLayout(self)
        root.setContentsMargins(FLUENT_H_MARGIN, FLUENT_V_MARGIN + 8,
                                FLUENT_H_MARGIN, FLUENT_V_MARGIN)
        root.setSpacing(SECTION_GAP)

        # ── 标题区域 ──
        title = TitleLabel("仪器设置")
        root.addWidget(title)

        subtitle = SubtitleLabel("管理和配置测试仪器的连接参数")
        root.addWidget(subtitle)

        root.addSpacing(8)

        # ── 三张仪器卡片 ──
        self._dmm_card = self._build_dmm_card()
        self._ps_card = self._build_ps_card()
        self._relay_card = self._build_relay_card()

        root.addWidget(self._dmm_card)
        root.addWidget(self._ps_card)
        root.addWidget(self._relay_card)

        root.addSpacing(4)

        # ── 底部按钮栏 ──
        root.addLayout(self._build_button_bar())

    def _setup_window_style(self):
        """根据明暗主题设置对话框背景。"""
        dark = isDarkTheme()
        if dark:
            self.setStyleSheet("""
                QDialog {
                    background-color: #1e1e1e;
                }
            """)
        else:
            self.setStyleSheet("""
                QDialog {
                    background-color: #f5f5f5;
                }
            """)

    # ── 各仪器卡片构建 ──

    def _build_dmm_card(self) -> _InstrumentCard:
        card = _InstrumentCard("34970A 数字万用表", "⎔")
        card.add_port_row("dmm_port", "USB 端口", self._mgr.config.get("dmm_port", ""))
        card.add_port_row("dmm_gpib", "GPIB 地址", self._mgr.config.get("dmm_gpib", "11"))
        card.add_mode_selector("dmm_mode", [
            ("usb",  "USB",  "dmm_port"),
            ("gpib", "GPIB", "dmm_gpib"),
        ])
        # 根据当前模式设置 ComboBox 初始值并切换可见性
        current_mode = self._mgr.config.get("dmm_mode", "usb")
        idx = card._mode_combo.findData(current_mode)
        if idx >= 0:
            card._mode_combo.setCurrentIndex(idx)
        card._on_mode_changed()
        self._cards["34970A"] = card
        card.signal_reconnect.connect(self.signal_reconnect.emit)
        return card

    def _build_ps_card(self) -> _InstrumentCard:
        card = _InstrumentCard("IT6382 程控电源", "⚡")
        card.add_port_row("ps_port", "GPIB 地址", self._mgr.config.get("ps_port", ""))
        self._cards["IT6382"] = card
        card.signal_reconnect.connect(self.signal_reconnect.emit)
        return card

    def _build_relay_card(self) -> _InstrumentCard:
        card = _InstrumentCard("Relayboard 继电器板", "⊞")
        card.add_port_row("relay_port", "USB 端口", self._mgr.config.get("relay_port", ""))
        card.add_port_row("relay_version", "版本号", self._mgr.config.get("relay_version", "0"))
        self._cards["Relayboard"] = card
        card.signal_reconnect.connect(self.signal_reconnect.emit)
        return card

    def _build_button_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.setSpacing(ELEMENT_GAP)
        bar.setContentsMargins(0, 4, 0, 0)

        bar.addStretch()

        reconnect_all_btn = PushButton(FluentIcon.SYNC, "  全部重连")
        reconnect_all_btn.setFixedHeight(BUTTON_HEIGHT)
        reconnect_all_btn.setToolTip("断开并重新检测所有仪器")
        reconnect_all_btn.clicked.connect(lambda: self.signal_reconnect.emit(""))
        bar.addWidget(reconnect_all_btn)

        cancel_btn = PushButton("取消")
        cancel_btn.setFixedHeight(BUTTON_HEIGHT)
        cancel_btn.clicked.connect(self.reject)
        bar.addWidget(cancel_btn)

        save_btn = PrimaryPushButton(FluentIcon.SAVE, "  保存")
        save_btn.setFixedHeight(BUTTON_HEIGHT)
        save_btn.clicked.connect(self._on_save)
        bar.addWidget(save_btn)

        return bar

    # ── 数据加载 / 保存 ──

    def _load_config(self):
        cfg = self._mgr.config
        for card in self._cards.values():
            for key in card.get_port_values():
                card.set_port_value(key, str(cfg.get(key, "")))

    def _on_save(self):
        """持久化所有端口配置并关闭。"""
        for card in self._cards.values():
            for key, val in card.get_port_values().items():
                if val:
                    self._mgr.update_config(**{key: val})
        self.accept()

    # ── 外部接口 ──

    def set_device_status(self, device_name: str, connected: bool, detail: str):
        """外部调用：更新指定仪器卡片的状态。"""
        card = self._cards.get(device_name)
        if card:
            card.set_status(connected, detail)

    # ── 信号连接 ──

    def _connect_signals(self):
        self._mgr.signal_device_status.connect(self.set_device_status)
