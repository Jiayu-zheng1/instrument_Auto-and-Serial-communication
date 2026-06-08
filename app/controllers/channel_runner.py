"""ChannelRunner — 单通道测试执行器，每个通道独立 QThread + DUT + 测试序列。"""

from PyQt5.QtCore import QThread, pyqtSignal
from app.utils.logger import get_logger

logger = get_logger("ChannelRunner")
from app.models.test_item import TestItem
from app.models.test_config import TestConfig, load_test_configs
from app.models.device import find_port_by_location
from app.utils.config import load_config


class ChannelRunner(QThread):
    """单通道测试线程：独立 DUT 连接、独立测试序列、独立信号。"""

    # 测试结果信号 (channel_id, display_name, value)
    signal_value = pyqtSignal(str, str, str)
    # PASS/FAIL 信号 (channel_id, display_name, result_text)
    signal_result = pyqtSignal(str, str, str)
    # 行颜色信号 (channel_id, display_name, "Pass"/"Fail")
    signal_color = pyqtSignal(str, str, str)
    # 单个通道测试完成 (channel_id, overall_pass)
    signal_channel_done = pyqtSignal(str, bool)
    # 日志信号 (channel_id, message)
    signal_log = pyqtSignal(str, str)
    # SN 显示 (channel_id, scan_sn, fgsn)
    signal_display = pyqtSignal(str, str, str)

    def __init__(self, channel_id: str, csv_rows: list[dict],
                 location_id: str = "",
                 instrument_manager=None, sn: str = "", fail_stop: bool = True):
        super().__init__()
        self._channel_id = channel_id
        self._csv_rows = csv_rows
        self._location_id = location_id  # USB location ID，空则自动取第一个串口
        self._sn = sn
        self._fail_stop = fail_stop
        self._test_status = True
        self.test_unit = TestItem(instrument_manager=instrument_manager)
        self.configs: list[TestConfig] = []
        self.FGSN: str = ""
        self._log_lines: list[str] = []
        self._last_value = None

    def run(self):
        loc_str = self._location_id or "auto"
        self._log(f"通道 {self._channel_id} 开始测试 (location={loc_str})")

        # 按 location_id 查找该通道的串口
        # 有 location_id 但没找到 → _dut_port=None → connent_dut 直接返回 False
        # 无 location_id → _dut_port="__unset__" → connent_dut 自动探测（兼容旧逻辑）
        if self._location_id:
            port = find_port_by_location(self._location_id)
            if port is None:
                self._log(f"  [{self._channel_id}] ⚠ 未找到 DUT 串口 (location={loc_str})")
            else:
                self._log(f"  [{self._channel_id}] DUT 串口: {port}")
            self.test_unit._dut_port = port  # None 或 str
        else:
            self.test_unit._dut_port = "__unset__"  # 自动探测

        # SN 加通道后缀，方便区分测试结果归属
        channel_sn = f"{self._sn}_{self._channel_id}" if self._sn else self._channel_id

        self._test_status = True
        self.test_unit.ScanSN = channel_sn
        self._load_configs()

        for cfg in self.configs:
            try:
                display = cfg.test_item
                method = cfg.test_name
                self._log(f"  [{self._channel_id}] {display} → {method}")
                value = self._run_one(display, method, cfg.config)

                if value is not None:
                    self._evaluate_result(display, str(value), cfg)
                else:
                    self.signal_value.emit(self._channel_id, display, "None")
                    self.signal_result.emit(self._channel_id, display, "Fail")
                    self.signal_color.emit(self._channel_id, display, "Fail")
                    self._test_status = False

            except Exception as e:
                self._log(f"  [{self._channel_id}] 错误: {cfg.test_item} — {e}")
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

    def _run_one(self, display: str, method: str, config: dict):
        if method == "run_read_cmd":
            raw_hex, ascii_str, value = self.test_unit.run_read_cmd(method, config)
        elif config:
            raw_hex, ascii_str, value = self.test_unit.run_read_cmd(method, config)
        elif hasattr(self.test_unit, method):
            test_function = getattr(self.test_unit, method)
            value = test_function()
            raw_hex, ascii_str = "", ""
        else:
            self._log(f"  [{self._channel_id}] 无 config 且无方法 '{method}' — 跳过")
            value = None
            raw_hex, ascii_str = "", ""

        if config.get("hex_cmd") and raw_hex:
            self._log(f"  [{self._channel_id}] raw: {raw_hex} | ascii: {ascii_str}")

        self._last_value = value
        return value

    def _evaluate_result(self, test_item: str, value: str, cfg: TestConfig):
        passed, label = cfg.evaluate(value)
        self.signal_value.emit(self._channel_id, test_item, value)
        self.signal_result.emit(self._channel_id, test_item, label)
        self.signal_color.emit(self._channel_id, test_item, label)
        if not passed:
            self._test_status = False

    def _log(self, msg: str):
        """写入通道日志缓冲并发射信号。"""
        self._log_lines.append(msg)
        logger.info(msg)
        self.signal_log.emit(self._channel_id, msg)

    def get_log_lines(self) -> list[str]:
        return list(self._log_lines)
