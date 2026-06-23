"""ChannelRunner — 多通道测试执行器，每个通道独立线程 + DUT + 测试序列。"""

from PyQt5.QtCore import pyqtSignal
from app.utils.logger import get_logger

logger = get_logger("ChannelRunner")
from app.controllers.base_runner import BaseTestRunner
from app.models.test_item import TestItem
from app.models.test_config import TestConfig, load_test_configs
from app.models.test_plan import TestStep
from app.models.device import find_port_by_location
from app.utils.config import load_config


class ChannelRunner(BaseTestRunner):
    """多通道测试线程：独立 DUT 连接、独立测试序列、独立信号（带 channel_id 前缀）。"""

    signal_value = pyqtSignal(str, str, str)
    signal_result = pyqtSignal(str, str, str)
    signal_color = pyqtSignal(str, str, str)
    signal_channel_done = pyqtSignal(str, bool)
    signal_log = pyqtSignal(str, str)
    signal_display = pyqtSignal(str, str, str)

    def __init__(self, channel_id: str, csv_rows: list[TestStep],
                 location_id: str = "",
                 instrument_manager=None, sn: str = "", fail_stop: bool = True,
                 dmm=None, ps=None, relay=None):
        super().__init__()
        self._channel_id = channel_id
        self._csv_rows = csv_rows
        self._location_id = location_id
        self._sn = sn
        self._fail_stop = fail_stop
        self._test_status = True
        self.test_unit = TestItem(
            instrument_manager=instrument_manager, dmm=dmm, ps=ps, relay=relay,
        )
        self.configs: list[TestConfig] = []
        self.FGSN: str = ""
        self._log_lines: list[str] = []
        self._last_value = None

    # ── 钩子实现 ──

    def _emit_value(self, test_item: str, value: str):
        self.signal_value.emit(self._channel_id, test_item, value)

    def _emit_result(self, test_item: str, label: str):
        self.signal_result.emit(self._channel_id, test_item, label)

    def _emit_color(self, test_item: str, color: str):
        self.signal_color.emit(self._channel_id, color)

    def _log(self, msg: str):
        self._log_lines.append(msg)
        logger.info(msg)
        self.signal_log.emit(self._channel_id, msg)

    # ── 主循环 ──

    def run(self):
        loc_str = self._location_id or "auto"
        self._log(f"通道 {self._channel_id} 开始测试 (location={loc_str})")

        if self._location_id:
            port = find_port_by_location(self._location_id)
            if port is None:
                self._log(f"  [{self._channel_id}] ⚠ 未找到 DUT 串口 (location={loc_str})")
            else:
                self._log(f"  [{self._channel_id}] DUT 串口: {port}")
            self.test_unit._dut_port = port
        else:
            self.test_unit._dut_port = "__unset__"

        channel_sn = f"{self._sn}_{self._channel_id}" if self._sn else self._channel_id
        self._test_status = True
        self.test_unit.ScanSN = channel_sn
        self._load_configs()

        for cfg in self.configs:
            try:
                display = cfg.sub_test_name
                method = cfg.function
                self._log(f"  [{self._channel_id}] {display} → {method}")
                value = self._run_one(display, method, cfg.config)

                if value is not None:
                    self._evaluate_result(display, str(value), cfg)
                else:
                    display_value = "FAILED" if cfg.is_special_limit() else "None"
                    self.signal_value.emit(self._channel_id, display, display_value)
                    self.signal_result.emit(self._channel_id, display, "Fail")
                    self.signal_color.emit(self._channel_id, display, "Fail")
                    self._test_status = False

            except Exception as e:
                self._log(f"  [{self._channel_id}] 错误: {cfg.sub_test_name} — {e}")
                display_value = "FAILED" if cfg.is_special_limit() else str(e)
                self.signal_value.emit(self._channel_id, display, display_value)
                self.signal_result.emit(self._channel_id, display, "Fail")
                self.signal_color.emit(self._channel_id, display, "Fail")
                self._test_status = False

            if self._fail_stop and not self._test_status:
                self._log(f"  [{self._channel_id}] Fail-stop 已启用，停止后续测试")
                break

            if self.test_unit.FGSN:
                self.FGSN = f"{self.test_unit.FGSN}_{self._channel_id}"
                self.signal_display.emit(self._channel_id, channel_sn, self.FGSN)

        self.test_unit.close_dut()
        status_text = "PASS" if self._test_status else "FAIL"
        self._log(f"通道 {self._channel_id} 测试完成: {status_text}")
        self.signal_channel_done.emit(self._channel_id, self._test_status)

    def _load_configs(self):
        self.configs = load_test_configs(self._csv_rows)
        self.test_items = [c.sub_test_name for c in self.configs]
        self.lower_limit_map = {
            c.sub_test_name: c.lower_limit_raw for c in self.configs
        }
        self.upper_limit_map = {
            c.sub_test_name: c.upper_limit_raw for c in self.configs
        }

    def get_log_lines(self) -> list[str]:
        return list(self._log_lines)
