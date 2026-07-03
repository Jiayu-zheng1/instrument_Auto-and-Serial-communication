"""模块化 Logger — 按天分文件，历史日志归档到日期文件夹。

目录结构:
    ~/Documents/SpartaLog/TopLevelLog/
    ├── InstrumentManager.log          ← 今天的活跃日志
    ├── ChannelRunner.log
    ├── 2026-06-02/                    ← 历史：每天一个文件夹
    │   ├── InstrumentManager.log
    │   └── ChannelRunner.log
    └── 2026-06-01/
        └── ...

用法:
    from app.utils.logger import get_logger
    logger = get_logger("DUT")
    logger.info("消息")
"""

from loguru import logger as _logger
from pathlib import Path
import re as _re
import sys
import os
import threading
import time
import shutil

# loguru 轮转后的文件名: ModuleName.2026-06-24_16-37-03_787290.log
_ROTATED_RX = _re.compile(r"^(.+?)\.(\d{4}-\d{2}-\d{2})_.+\.log$")

# ═══════════════════════════════════════════════════════════════════════════
#  常量
# ═══════════════════════════════════════════════════════════════════════════

LOG_DIR = Path(os.path.expanduser("~/Documents/SpartaLog/TopLevelLog"))
ARCHIVE_DIR = Path(os.path.expanduser("~/Documents/SpartaLog/unit-archive"))

# ═══════════════════════════════════════════════════════════════════════════
#  全局状态
# ═══════════════════════════════════════════════════════════════════════════

_initialized = False
_init_lock = threading.Lock()
_module_ids: dict[str, int] = {}

_worker_started = False
_worker_lock = threading.Lock()

# 单pcs 测试日志
_unit_log_dir: Path | None = None    # 当前单元测试文件夹路径
_unit_handler_id: int | None = None  # 单元日志 handler ID


# ═══════════════════════════════════════════════════════════════════════════
#  后台归档工作线程
# ═══════════════════════════════════════════════════════════════════════════

def _archive_worker():
    """每分钟扫描一次：把轮转后的旧日志移入日期文件夹 + 清理过期日期文件夹。"""
    from app.utils.config import load_config

    while True:
        time.sleep(60)
        try:
            cfg = load_config()
            keep_days = cfg.get("log_retention_days", 90)
            cutoff = time.time() - keep_days * 86400

            # 扫描 loguru 轮转产生的旧文件: ModuleName.2026-06-24_16-37-03_787290.log
            for f in LOG_DIR.glob("*.log"):
                name = f.name
                m = _ROTATED_RX.match(name)
                if not m:
                    continue  # 跳过活跃日志（ModuleName.log 不带时间戳）
                base = m.group(1)
                date_str = m.group(2)  # "2026-06-24"

                date_dir = LOG_DIR / date_str
                date_dir.mkdir(parents=True, exist_ok=True)
                dst = date_dir / f"{base}.log"

                # 如果目标已存在，合并追加（同一天多次轮转）
                if dst.exists():
                    with open(f, "r", encoding="utf-8", errors="ignore") as src_f:
                        with open(dst, "a", encoding="utf-8") as dst_f:
                            dst_f.write(src_f.read())
                    f.unlink()
                else:
                    shutil.move(str(f), str(dst))

            # 清理过期的日期文件夹
            for date_dir in LOG_DIR.iterdir():
                if not date_dir.is_dir():
                    continue
                if len(date_dir.name) != 10 or date_dir.name[4] != "-":
                    continue  # 不是 YYYY-MM-DD 格式，跳过
                try:
                    # 如果文件夹内所有文件都早于截止时间，删除整个文件夹
                    files = list(date_dir.iterdir())
                    if files and all(
                        f.stat().st_mtime < cutoff for f in files if f.is_file()
                    ):
                        shutil.rmtree(date_dir)
                except Exception:
                    pass
        except Exception:
            pass


def _start_worker():
    threading.Thread(target=_archive_worker, daemon=True).start()


def _ensure_worker():
    global _worker_started
    if _worker_started:
        return
    with _worker_lock:
        if _worker_started:
            return
        _start_worker()
        _worker_started = True


# ═══════════════════════════════════════════════════════════════════════════
#  初始化（全局一次）
# ═══════════════════════════════════════════════════════════════════════════

def _init_once():
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return

        LOG_DIR.mkdir(parents=True, exist_ok=True)

        _logger.remove()

        _logger.add(
            sys.stdout,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SS}</green> | "
                "<level>{level:<5}</level> | "
                "<cyan>{extra[module]}</cyan> | "
                "{message}"
            ),
            level="INFO",
            colorize=True,
        )

        _ensure_worker()
        _initialized = True


# ═══════════════════════════════════════════════════════════════════════════
#  Public API
# ═══════════════════════════════════════════════════════════════════════════

def ensure_module(module_name: str):
    """为模块创建日志文件 handler（幂等）。"""
    _init_once()

    if module_name in _module_ids:
        return

    log_file = LOG_DIR / f"{module_name}.log"

    file_id = _logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<5} | {message}",
        level="DEBUG",
        rotation="00:00",           # 每天午夜轮转
        retention=90,                # 保留最近90个轮转文件，给 worker 充足时间搬运
        compression=None,
        encoding="utf-8",
        enqueue=True,
        filter=lambda r, name=module_name: r["extra"].get("module") == name,
    )
    _module_ids[module_name] = file_id


def get_logger(module_name: str):
    """返回绑定模块名的 logger，用法同 loguru.logger。"""
    ensure_module(module_name)
    return _logger.bind(module=module_name)


# ═══════════════════════════════════════════════════════════════════════════
#  单pcs 日志归档 — 每 pcs 一个文件夹
# ═══════════════════════════════════════════════════════════════════════════

def make_unit_folder(scan_sn: str = "", fgsn: str = "", mlbsn: str = "") -> Path:
    """创建单pcs测试的日志文件夹。

    目录名优先级: 扫描SN → DUT读取SN → 时间戳
    重复 SN 自动追加时间戳后缀: GVVG93V6JH_20260624_143000

    Returns:
        创建的文件夹 Path
    """
    name = scan_sn or fgsn or mlbsn or time.strftime("%Y%m%d_%H%M%S")
    target = ARCHIVE_DIR / name
    if target.exists():
        name = f"{name}_{time.strftime('%Y%m%d_%H%M%S')}"
    unit_dir = ARCHIVE_DIR / name
    unit_dir.mkdir(parents=True, exist_ok=True)
    return unit_dir


def begin_unit_log(unit_dir: Path):
    """为当前单元测试开启独立日志 — 所有模块日志统一写入 unit_dir/test.log。"""
    global _unit_log_dir, _unit_handler_id
    _init_once()  # 确保 _init_once 已完成，避免后续 initialize 清掉我们的 handler
    _unit_log_dir = unit_dir
    _unit_handler_id = _logger.add(
        unit_dir / "test.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<5} | {extra[module]} | {message}",
        level="DEBUG",
        encoding="utf-8",
    )


def end_unit_log():
    """结束单元日志 — 关闭 unit 目录 handler。"""
    global _unit_log_dir, _unit_handler_id
    if _unit_handler_id is not None:
        try:
            _logger.remove(_unit_handler_id)
        except Exception:
            pass
    _unit_handler_id = None
    _unit_log_dir = None


def get_unit_log_dir() -> Path | None:
    """返回当前单元日志目录（供 CsvReport 等写入 records.csv）。"""
    return _unit_log_dir
