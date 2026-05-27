"""Test runner — QThread-based test execution engine."""
import time
from PyQt5.QtCore import QThread, pyqtSignal
from loguru import logger
from app.models.test_item import TestItem
from app.models.test_config import TestConfig, load_test_configs
from app.utils.csv_handler import CsvReport


class TestRunner(QThread):
    """Runs test items in sequence on a background thread."""

    signal_value = pyqtSignal(str, str)
    signal_result = pyqtSignal(str, str)
    signal_color = pyqtSignal(str, str)
    signal_status = pyqtSignal(bool)
    signal_stop = pyqtSignal()
    signal_display = pyqtSignal(str, str)

    def __init__(self, csv_rows: list[dict], log_controller):
        super().__init__()
        self._csv_rows = csv_rows
        self._log_controller = log_controller
        self.ScanSN: str = None
        self.test_unit = TestItem()
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
        csv_report = CsvReport(self.test_items, self.upper_limit_map, self.lower_limit_map)

        for cfg in self.configs:
            try:
                test_item = cfg.test_item
                logger.info(f"Running test item: {test_item}")
                value = self._run_one(test_item, cfg.config)

                if value is not None:
                    self._evaluate_result(test_item, str(value), cfg)
                else:
                    self.signal_value.emit(test_item, "None")
                    self.signal_result.emit(test_item, "Fail")
                    self.signal_color.emit(test_item, "Fail")
                    self._test_status = False

            except Exception as e:
                logger.info(f"Error running test item {cfg.test_item}: {e}")

            if self.test_unit.FGSN:
                self.signal_display.emit(self.ScanSN, self.test_unit.FGSN)

        csv_report.set_csv_file(self.test_unit.FGSN,
                                {c.test_item: getattr(self, '_last_value', None) for c in self.configs})
        self.stop()

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

    def _run_one(self, test_item: str, config: dict):
        if config:
            value = self.test_unit.run_by_config(test_item, config)
        else:
            test_function = getattr(self.test_unit, test_item)
            value = test_function()
        self._last_value = value
        return value

    def _evaluate_result(self, test_item: str, value: str, cfg: TestConfig):
        passed, label = cfg.evaluate(value)
        self.signal_value.emit(test_item, value)
        self.signal_result.emit(test_item, label)
        self.signal_color.emit(test_item, label)
        if not passed:
            self._test_status = False
