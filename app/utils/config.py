"""统一系统配置 — 单一入口读写 ~/Documents/SpartaLog/system_config.json。

用法:
    from app.utils.config import load_config, save_config
    cfg = load_config()
    fail_stop = cfg.get("fail_stop_test", True)
    cfg["fail_stop_test"] = False
    save_config(cfg)
"""

import json
import os
from app.utils.constants import CONFIG_DIR

SYSTEM_CONFIG_PATH = os.path.join(CONFIG_DIR, "system_config.json")

DEFAULTS = {
    "log_retention_days": 90,
    "dut_baud_rate": 921600,
    "dut_location_id": "",
    "auto_test_mode": False,
    "fail_stop_test": True,
    "auto_scroll_log": True,
    "sfc_url": "",
    "sfc_online": False,
    "sfc_vip": "",
    # 多通道测试
    "multi_channel_mode": False,        # 是否启用多通道模式
    "channel_count": 4,                 # 通道数量 (1-8)
    "channel_location_ids": ["", "", "", ""],  # 每个通道的 DUT location ID
    "channel_instruments": ["", "", "", ""],   # 每个通道绑定的仪器名，空=无仪器
    # 多 DMM 实例端口（按通道数自动展开）
    "dmm_instances": [                  # 每台 34970A 的独立配置
        {"mode": "usb", "port": "/dev/cu.usbserial-FTDH1RD8", "gpib": "11"},
    ],
}


def load_config() -> dict:
    """加载系统配置，合并默认值。"""
    cfg = dict(DEFAULTS)
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        if os.path.exists(SYSTEM_CONFIG_PATH):
            with open(SYSTEM_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
    except Exception:
        pass
    return cfg


def save_config(cfg: dict):
    """持久化系统配置到 JSON 文件。"""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(SYSTEM_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception:
        pass
