"""Log controller — loguru initialization and Qt signal bridging."""
import sys
import os
import datetime
import shutil
from PyQt5.QtCore import QObject, pyqtSignal
from loguru import logger


class LogHandler(QObject):
    _Test_log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()

    def write(self, message):
        self._Test_log_signal.emit(message.strip())

    def flush(self):
        pass


class LogController:
    """Manages loguru configuration and signal-based log output."""

    FORMAT = '{time:YYYY-MM-DD HH:mm:ss.SS} | {level:<5} | {message}'

    def __init__(self, log_path: str):
        self.log_file_id = None
        self.log_path = log_path
        self.logname = None
        self.log_file_path = None
        self.logger_initialized = False

    def initialize(self):
        os.makedirs(self.log_path, exist_ok=True)
        if not self.logger_initialized:
            logger.remove()
            # 控制台只显示 INFO 及以上级别
            logger.add(sys.stdout, format=self.FORMAT, level="INFO")
            self._path_logger()
            self.logger_initialized = True

    def rename_log(self, sn: str = ''):
        if hasattr(self, 'log_file_path') and self.log_file_path:
            rename = os.path.join(
                self.log_path,
                f"{sn}{os.path.basename(self.log_file_path)}"
            )
            shutil.move(self.log_file_path, rename)

    def _path_logger(self):
        if hasattr(self, 'log_file_id') and self.log_file_id:
            logger.remove(self.log_file_id)
        self.logname = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file_path = os.path.join(self.log_path, f'_{self.logname}.log')
        # 日志文件记录 DEBUG 及以上级别（包含原始返回值和 ASCII 值）
        self.log_file_id = logger.add(
            self.log_file_path, rotation="1 day", encoding="utf-8", retention="90 days",
            level="DEBUG"
        )

    def bind_signal(self, log_slot):
        """Connect logger output to a Qt slot (e.g. append to QTextEdit)."""
        self.log_handler = LogHandler()
        self.log_handler._Test_log_signal.connect(log_slot)
        logger.add(self.log_handler, format=self.FORMAT)
