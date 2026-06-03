"""仪器管理器 — 单例模式，管理 34970A / IT6382 / Relayboard 的连接和状态。
支持多通道：每个通道可绑定独立的 DMM 实例（如 34970A_1, 34970A_2）。
"""

import json
import os
import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal
from app.utils.logger import get_logger

logger = get_logger("InstrumentManager")

from app.models.instruments.keysight_34970a import KEYSIGHT_34970A
from app.models.instruments.ps_it6382 import IT6382
from app.models.instruments.relay_board import RELAYBOARD
from app.utils.constants import INSTRUMENT_CONFIG_PATH
from app.utils.config import load_config


# ── 默认配置 ──────────────────────────────────────────────────────────
DEFAULT_CONFIG = {
    "dmm_mode": "usb",
    "dmm_port": "/dev/cu.usbserial-FTDH1RD8",
    "dmm_gpib": "11",
    "ps_mode": "gpib",
    "ps_port": "8",
    "ps_usb_port": "",
    "relay_port": "/dev/cu.usbserial-AL02P374",
    "relay_version": "0",
}

DEVICE_CHECK_TIMEOUT = 3


class InstrumentManager(QObject):
    """仪器管理器单例。支持多台 34970A 一对一绑定通道。"""

    signal_device_status = pyqtSignal(str, bool, str)
    signal_all_checked = pyqtSignal()

    _instance = None

    @classmethod
    def instance(cls) -> "InstrumentManager":
        if cls._instance is None:
            cls._instance = InstrumentManager()
        return cls._instance

    def __init__(self, parent=None):
        if InstrumentManager._instance is not None:
            raise RuntimeError(
                "InstrumentManager is a singleton — use InstrumentManager.instance()"
            )
        super().__init__(parent)
        InstrumentManager._instance = self

        # 仪器实例 — DMM 支持多个
        self._dmm_list: list[KEYSIGHT_34970A | None] = []
        self._dmm_connected_list: list[bool] = []
        self._ps: IT6382 | None = None
        self._relay: RELAYBOARD | None = None

        # 状态
        self._ps_connected = False
        self._relay_connected = False
        self._checking = False
        self._config = dict(DEFAULT_CONFIG)
        self._load_config()

    # ── 配置 ──────────────────────────────────────────────────────────

    @property
    def config(self) -> dict:
        return self._config

    def _load_config(self):
        try:
            if os.path.exists(INSTRUMENT_CONFIG_PATH):
                with open(INSTRUMENT_CONFIG_PATH, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._config.update(saved)
                logger.info(f"仪器配置已从 {INSTRUMENT_CONFIG_PATH} 加载")
        except Exception as e:
            logger.warning(f"加载仪器配置失败: {e}")

    def _save_config(self):
        try:
            os.makedirs(os.path.dirname(INSTRUMENT_CONFIG_PATH), exist_ok=True)
            with open(INSTRUMENT_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info(f"仪器配置已保存到 {INSTRUMENT_CONFIG_PATH}")
        except Exception as e:
            logger.warning(f"保存仪器配置失败: {e}")

    def update_config(self, **kwargs):
        for k, v in kwargs.items():
            if k in self._config:
                self._config[k] = v
        self._save_config()
        logger.info(f"InstrumentManager config updated: {self._config}")

    # ── DMM 实例列表 ──────────────────────────────────────────────────

    def _get_dmm_instances(self) -> list[dict]:
        """从 system_config.json 读取所有 DMM 实例配置。
        兼容旧格式：如果没有 dmm_instances，用 instrument_config 的 dmm_* 构建单实例。
        """
        sys_cfg = load_config()
        dmm_list = sys_cfg.get("dmm_instances", [])
        if not dmm_list:
            # 兼容旧格式
            dmm_list = [{
                "mode": self._config.get("dmm_mode", "usb"),
                "port": self._config.get("dmm_port", "/dev/cu.usbserial-FTDH1RD8"),
                "gpib": self._config.get("dmm_gpib", "11"),
            }]
        return dmm_list

    @property
    def dmm_count(self) -> int:
        return len(self._get_dmm_instances())

    # ── 仪器访问 ──────────────────────────────────────────────────────

    @property
    def dmm(self) -> KEYSIGHT_34970A | None:
        """返回第一台 DMM（单通道兼容）。"""
        if self._dmm_list and len(self._dmm_connected_list) > 0 and self._dmm_connected_list[0]:
            return self._dmm_list[0]
        return None

    def get_dmm(self, index: int = 0) -> KEYSIGHT_34970A | None:
        """按索引获取 DMM 实例。index=0 是第一台..."""
        if 0 <= index < len(self._dmm_list) and index < len(self._dmm_connected_list):
            return self._dmm_list[index] if self._dmm_connected_list[index] else None
        return None

    @property
    def ps(self) -> IT6382 | None:
        return self._ps if self._ps_connected else None

    @property
    def relay(self) -> RELAYBOARD | None:
        return self._relay if self._relay_connected else None

    @property
    def dmm_connected(self) -> bool:
        """第一台 DMM 是否连接（单通道兼容）。"""
        return len(self._dmm_connected_list) > 0 and self._dmm_connected_list[0]

    def dmm_instance_connected(self, index: int) -> bool:
        if 0 <= index < len(self._dmm_connected_list):
            return self._dmm_connected_list[index]
        return False

    @property
    def ps_connected(self) -> bool:
        return self._ps_connected

    @property
    def relay_connected(self) -> bool:
        return self._relay_connected

    @property
    def all_connected(self) -> bool:
        return self.dmm_connected and self._ps_connected and self._relay_connected

    # ── 自动检测（后台线程）────────────────────────────────────────────

    def start_auto_check(self):
        if self._checking:
            return
        self._checking = True
        logger.info("InstrumentManager: 开始自动检测仪器...")
        thread = threading.Thread(target=self._auto_check_devices, daemon=True)
        thread.start()

    def _auto_check_devices(self):
        self._check_all_dmms()
        self._check_it6382()
        self._check_relayboard()
        self._checking = False
        self.signal_all_checked.emit()
        logger.info("InstrumentManager: 仪器检测完成")

    # ── DMM 检测 ──────────────────────────────────────────────────────

    def _check_all_dmms(self):
        """检测所有配置的 34970A 实例。"""
        dmm_instances = self._get_dmm_instances()
        self._dmm_list = [None] * len(dmm_instances)
        self._dmm_connected_list = [False] * len(dmm_instances)

        for i, inst_cfg in enumerate(dmm_instances):
            self._check_one_dmm(i, inst_cfg)

    def _check_one_dmm(self, index: int, inst_cfg: dict):
        """检测单台 34970A。"""
        mode = inst_cfg.get("mode", "usb")
        if mode == "gpib":
            port = inst_cfg.get("gpib", "11")
        else:
            port = inst_cfg.get("port", "/dev/cu.usbserial-FTDH1RD8")

        dev_name = f"34970A_{index + 1}"
        self.signal_device_status.emit(dev_name, False, f"检测中 ({port})...")
        logger.info(f"检查 {dev_name} (模式: {mode}, 端口: {port})...")

        try:
            dmm = KEYSIGHT_34970A(gpipID=9, serial_port=port)
            if dmm.dmm_instrument():
                idn = dmm.query_IDN() or "IDN 查询失败"
                dmm.set_DMMcls()
                self._dmm_list[index] = dmm
                self._dmm_connected_list[index] = True
                self.signal_device_status.emit(dev_name, True, idn.strip())
                logger.info(f"{dev_name} 连接成功: {idn.strip()}")
            else:
                self.signal_device_status.emit(dev_name, False, "未找到仪器")
                logger.warning(f"{dev_name} 未找到仪器")
        except Exception as e:
            self.signal_device_status.emit(dev_name, False, f"错误: {e}")
            logger.error(f"{dev_name} 检测异常: {e}")

    def _check_it6382(self):
        mode = self._config.get("ps_mode", "gpib")
        if mode == "usb":
            port = self._config.get("ps_usb_port", "")
            label = f"USB:{port}" if port else "USB (auto)"
        else:
            port = self._config["ps_port"]
            label = f"GPIB:{port}"

        self.signal_device_status.emit("IT6382", False, f"检测中 ({label})...")
        logger.info(f"检查 IT6382 ({label})...")

        try:
            gpibid = port if mode == "gpib" else None
            ps = IT6382(gpibid) if gpibid else IT6382("")
            if ps.ps_instrument():
                idn = ps.query_IDN() or "IDN 查询失败"
                self._ps = ps
                self._ps_connected = True
                self.signal_device_status.emit("IT6382", True, idn.strip())
                logger.info(f"IT6382 连接成功: {idn.strip()}")
            else:
                self.signal_device_status.emit("IT6382", False, "未找到仪器")
                logger.warning("IT6382 未找到仪器")
        except Exception as e:
            self._ps_connected = False
            self.signal_device_status.emit("IT6382", False, f"错误: {e}")
            logger.error(f"IT6382 检测异常: {e}")

    def _check_relayboard(self):
        port = self._config["relay_port"]
        version = self._config["relay_version"]
        self.signal_device_status.emit("Relayboard", False, f"检测中 ({port})...")
        logger.info(f"检查 Relayboard ({port}, v{version})...")

        try:
            relay = RELAYBOARD(version, port)
            relay.init_board()
            if relay.ser and relay.ser.is_open:
                relay.turn_off_relays(range(1, 9))
                self._relay = relay
                self._relay_connected = True
                self.signal_device_status.emit(
                    "Relayboard", True, f"{port} (v{version})"
                )
                logger.info(f"Relayboard 连接成功: {port}")
            else:
                self.signal_device_status.emit("Relayboard", False, f"无法打开 {port}")
                logger.warning(f"Relayboard 连接失败: {port}")
        except Exception as e:
            self._relay_connected = False
            self.signal_device_status.emit("Relayboard", False, f"错误: {e}")
            logger.error(f"Relayboard 检测异常: {e}")

    # ── 手动重连 ──────────────────────────────────────────────────────

    def reconnect_device(self, device_name: str):
        """手动重新连接指定仪器。device_name 如 '34970A_1' 或 '34970A'。"""
        if device_name.startswith("34970A"):
            idx = _parse_dmm_index(device_name)
            self._disconnect_dmm(idx)
            dmm_list = self._get_dmm_instances()
            if 0 <= idx < len(dmm_list):
                self._check_one_dmm(idx, dmm_list[idx])
        elif device_name == "IT6382":
            self._disconnect_ps()
            self._check_it6382()
        elif device_name == "Relayboard":
            self._disconnect_relay()
            self._check_relayboard()

    def disconnect_device(self, device_name: str):
        """断开指定仪器并通知 UI。"""
        if device_name.startswith("34970A"):
            idx = _parse_dmm_index(device_name)
            self._disconnect_dmm(idx)
            self.signal_device_status.emit(device_name, False, "已断开")
        elif device_name == "IT6382":
            self._disconnect_ps()
            self.signal_device_status.emit("IT6382", False, "已断开")
        elif device_name == "Relayboard":
            self._disconnect_relay()
            self.signal_device_status.emit("Relayboard", False, "已断开")

    def reconnect_all(self):
        self._disconnect_all()
        thread = threading.Thread(target=self._auto_check_devices, daemon=True)
        thread.start()

    # ── 断开 ──────────────────────────────────────────────────────────

    def _disconnect_dmm(self, index: int = 0):
        if index < len(self._dmm_list) and self._dmm_list[index]:
            try:
                self._dmm_list[index].close()
            except Exception:
                pass
        if index < len(self._dmm_list):
            self._dmm_list[index] = None
        if index < len(self._dmm_connected_list):
            self._dmm_connected_list[index] = False

    def _disconnect_ps(self):
        if self._ps:
            try:
                self._ps.close()
            except Exception:
                pass
        self._ps = None
        self._ps_connected = False

    def _disconnect_relay(self):
        if self._relay:
            try:
                self._relay.close()
            except Exception:
                pass
        self._relay = None
        self._relay_connected = False

    def _disconnect_all(self):
        for i in range(len(self._dmm_list)):
            self._disconnect_dmm(i)
        self._disconnect_ps()
        self._disconnect_relay()

    def shutdown(self):
        self._disconnect_all()
        logger.info("InstrumentManager: 所有仪器已断开")


def _parse_dmm_index(device_name: str) -> int:
    """从设备名解析 DMM 索引。'34970A'→0, '34970A_1'→0, '34970A_2'→1。"""
    if "_" in device_name:
        try:
            return int(device_name.split("_")[1]) - 1
        except (ValueError, IndexError):
            pass
    return 0
