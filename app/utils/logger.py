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
import sys
import os
import threading
import time
import shutil

# ═══════════════════════════════════════════════════════════════════════════
#  常量
# ═══════════════════════════════════════════════════════════════════════════

LOG_DIR = Path(os.path.expanduser("~/Documents/SpartaLog/TopLevelLog"))

# ═══════════════════════════════════════════════════════════════════════════
#  全局状态
# ═══════════════════════════════════════════════════════════════════════════

_initialized = False
_init_lock = threading.Lock()
_module_ids: dict[str, int] = {}

_worker_started = False
_worker_lock = threading.Lock()


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

            # 扫描 loguru 轮转产生的旧文件: <Name>.log.<timestamp>
            for f in LOG_DIR.glob("*.log.*"):
                try:
                    name = f.name
                    # "InstrumentManager.log.2026-06-02_10-07-01_330179"
                    base, ts_suffix = name.split(".log.", 1)
                    date_str = ts_suffix[:10]  # "2026-06-02"

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
                except Exception:
                    pass

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
