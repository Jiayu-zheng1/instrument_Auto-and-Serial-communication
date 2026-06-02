"""模块化 Logger — 每个模块独立日志文件，统一控制台输出。
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
import queue
import shutil

# ═══════════════════════════════════════════════════════════════════════════
#  后台轮转搬运
# ═══════════════════════════════════════════════════════════════════════════

_rotate_q: "queue.Queue" = queue.Queue()
_initialized = False
_init_lock = threading.Lock()
_module_ids: dict[str, int] = {}
LOG_DIR = Path(os.path.expanduser("~/Documents/SpartaLog/TopLevelLog"))
ARCHIVE_DIR = LOG_DIR / "archive"


def _start_worker():
    def _worker():
        while True:
            src, archive_dir, keep_days = _rotate_q.get()
            try:
                sub_dir = archive_dir / Path(src).stem.split(".")[0]
                sub_dir.mkdir(parents=True, exist_ok=True)
                dst = sub_dir / Path(src).name
                for _ in range(10):
                    try:
                        shutil.move(src, dst)
                        break
                    except Exception:
                        time.sleep(0.2)
                cutoff = time.time() - keep_days * 86400
                for f in archive_dir.rglob("*.log"):
                    try:
                        if f.is_file() and f.stat().st_mtime < cutoff:
                            f.unlink(missing_ok=True)
                    except Exception:
                        pass
            finally:
                _rotate_q.task_done()

    threading.Thread(target=_worker, daemon=True).start()


_worker_started = False
_worker_lock = threading.Lock()


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
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

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

    # 轮转钩子：把旧文件移入 archive/
    def _rotate_hook(path: str):
        _rotate_q.put((Path(path), ARCHIVE_DIR, 90))

    file_id = _logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<5} | {message}",
        level="DEBUG",
        rotation="00:00",
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
