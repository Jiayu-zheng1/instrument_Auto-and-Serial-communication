"""Test runner — QThread-based test execution engine."""
from PyQt5.QtCore import QThread, pyqtSignal
from app.utils.logger import get_logger

logger = get_logger("TestRunner")
from app.models.test_item import TestItem
from app.models.test_config import TestConfig, load_test_configs
from app.models.sfc_connector import SFCConnector
from app.utils.csv_handler import CsvReport
from app.utils.config import load_config


class TestRunner(QThread):
    """Runs test items in sequence on a background thread."""

    signal_value = pyqtSignal(str, str)
    signal_result = pyqtSignal(str, str)
    signal_color = pyqtSignal(str, str)
    signal_status = pyqtSignal(bool)
    signal_stop = pyqtSignal()
    signal_display = pyqtSignal(str, str)

    def __init__(self, csv_rows: list[dict], log_controller, instrument_manager=None):
        super().__init__()
        self._csv_rows = csv_rows
        self._log_controller = log_controller
        self.ScanSN: str = None
        self.test_unit = TestItem(instrument_manager=instrument_manager)
        self.configs: list[TestConfig] = []
        self.test_items: list[str] = []
        self.lower_limit_map: dict = {}
        self.upper_limit_map: dict = {}

    def run(self):
        logger.info("Starting test")
        self._test_status = True
        self.test_unit.ScanSN = self.ScanSN
        self._load_configs()
        self._log_controller._path_logger()
        self._load_system_config()
        csv_report = CsvReport(self.test_items, self.upper_limit_map, self.lower_limit_map)

        for cfg in self.configs:
            try:
                display = cfg.test_item
                method = cfg.test_name
                logger.info(f"Running: {display} → {method}")
                value = self._run_one(display, method, cfg.config)

                if value is not None:
                    self._evaluate_result(display, str(value), cfg)
                else:
                    self.signal_value.emit(display, "None")
                    self.signal_result.emit(display, "Fail")
                    self.signal_color.emit(display, "Fail")
                    self._test_status = False

            except Exception as e:
                logger.info(f"Error running test item {cfg.test_item}: {e}")
                self._test_status = False

            # fail_stop_test：失败时立即停止后续测试
            if self._fail_stop and not self._test_status:
                logger.info("Fail-stop 已启用，停止后续测试")
                break

            if self.test_unit.FGSN:
                self.signal_display.emit(self.ScanSN, self.test_unit.FGSN)

        csv_report.set_csv_file(self.test_unit.FGSN,
                                {c.test_item: getattr(self, '_last_value', None) for c in self.configs})

        # 上报 SFC
        self._upload_sfc()

        self.stop()

    def _load_system_config(self):
        """统一加载系统配置。"""
        cfg = load_config()
        self._fail_stop = cfg.get("fail_stop_test", True)
        self._sfc_cfg = {
            "url": cfg.get("sfc_url", ""),
            "online": cfg.get("sfc_online", False),
            "vip": cfg.get("sfc_vip", ""),
        }
        logger.info(f"系统配置已加载: fail_stop={self._fail_stop}, sfc_online={self._sfc_cfg.get('online')}")

    def _upload_sfc(self):
        """向 SFC 上报测试结果（仅在线模式）。"""
        if not self._sfc_cfg.get("online") or not self._sfc_cfg.get("url"):
            return
        sn = self.ScanSN or self.test_unit.FGSN or ""
        if not sn:
            logger.info("SFC 上传跳过：无 SN")
            return
        try:
            sfc = SFCConnector(
                url=self._sfc_cfg["url"],
                vip=self._sfc_cfg["vip"],
                online=True,
            )
            sfc.connect()
            sfc.check_route(sn)
            sfc.upload_result(sn, self._test_status)
            logger.info(f"SFC 上传完成: SN={sn}, status={'PASS' if self._test_status else 'FAIL'}")
        except Exception as e:
            logger.error(f"SFC 上传失败: {e}")

    def stop(self):
        self.signal_status.emit(self._test_status)
        self.test_unit.close_dut()
        self.signal_stop.emit()
        self._log_controller.rename_log(self.test_unit.FGSN)

    def _load_configs(self):
        self.configs = load_test_configs(self._csv_rows)
        self.test_items = [c.test_item for c in self.configs]
        self.lower_limit_map = {c.test_item: c.lower_limit_raw for c in self.configs}
        self.upper_limit_map = {c.test_item: c.upper_limit_raw for c in self.configs}

    def _run_one(self, display: str, method: str, config: dict):
        # run_read_cmd 是通用配置处理器，总是走它（即使 config 为空也让它自己处理）
        if method == "run_read_cmd":
            raw_hex, ascii_str, value = self.test_unit.run_read_cmd(method, config)
        elif config:
            raw_hex, ascii_str, value = self.test_unit.run_read_cmd(method, config)
        elif hasattr(self.test_unit, method):
            test_function = getattr(self.test_unit, method)
            value = test_function()
            raw_hex, ascii_str = "", ""
        else:
            logger.info(f"No config and no method '{method}' — skipping")
            value = None
            raw_hex, ascii_str = "", ""

        # 记录原始返回值和 ASCII 值到日志文件（仅当有 hex_cmd 时）
        if config.get("hex_cmd") and raw_hex:
            logger.debug(f"[{display}] raw: {raw_hex} | ascii: {ascii_str}")

        self._last_value = value
        return value

    def _evaluate_result(self, test_item: str, value: str, cfg: TestConfig):
        passed, label = cfg.evaluate(value)
        self.signal_value.emit(test_item, value)
        self.signal_result.emit(test_item, label)
        self.signal_color.emit(test_item, label)
        if not passed:
            self._test_status = False
