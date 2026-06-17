"""双 CSV 加载器 — Main.csv(测试序列) + Limits.csv(判据) 按 SubTestName 合并。

用法:
    from app.utils.limits_loader import load_test_data
    headers, rows = load_test_data()
    # rows = [{"TestName":..., "Function":..., ..., "Limits": {...}, "config": {...}}, ...]
"""

import csv
import os
from app.utils.constants import MAIN_CSV, LIMITS_CSV
from app.utils.config_parser import parse_config


def load_limits_map() -> dict[str, dict]:
    """加载 Limits.csv → {SubTestName: {LowerLimit, UpperLimit, Unit, Visible}}"""
    limits = {}
    if not os.path.exists(LIMITS_CSV):
        return limits
    with open(LIMITS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sub = row.get("SubTestName", "").strip()
            if sub:
                limits[sub] = {
                    "LowerLimit": row.get("LowerLimit", "").strip(),
                    "UpperLimit": row.get("UpperLimit", "").strip(),
                    "Unit": row.get("Unit", "").strip(),
                    "Visible": row.get("Visible", "Y").strip(),
                }
    return limits


def load_test_data() -> tuple[list[str], list[dict]]:
    """加载 Main.csv + Limits.csv，合并后返回 (headers, rows)。

    Main.csv:  TestName, Function, SubTestName, Running, config
    Limits.csv:SubTestName, LowerLimit, UpperLimit, Unit, Visible

    合并后 row 包含:
      - Main.csv 所有字段
      - Limits: {LowerLimit, UpperLimit, Unit, Visible}
    """
    if not os.path.exists(MAIN_CSV):
        return [], []

    limits_map = load_limits_map()

    with open(MAIN_CSV, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        return [], []

    raw_headers = [h.strip() for h in lines[0].strip().split(",")]
    config_idx = raw_headers.index("config") if "config" in raw_headers else -1
    if config_idx < 0:
        return [], []

    rows = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(",", config_idx)
        if len(parts) < config_idx + 1:
            parts.extend([""] * (config_idx + 1 - len(parts)))

        row = {}
        for i in range(config_idx):
            row[raw_headers[i]] = parts[i].strip()
        config_text = parts[config_idx].strip().rstrip(",")
        row["config"] = parse_config(config_text)

        # ── 按 SubTestName 合并 Limits ──
        sub = row.get("SubTestName", "")
        limits = limits_map.get(sub, {})
        row["LowerLimit"] = limits.get("LowerLimit", "")
        row["UpperLimit"] = limits.get("UpperLimit", "")
        row["Unit"] = limits.get("Unit", "")
        row["Visible"] = limits.get("Visible", "Y")

        rows.append(row)

    # 供表格显示的列（Visible=N 的列也从表头中排除）
    visible_keys = {"Visible"}
    hidden = {"Running", "config", "Visible"}
    headers = [h for h in raw_headers if h not in hidden]
    # Limits列  + 运行时动态列（从何处来：表格显示用，but从CSV加载时为空）
    headers += ["LowerLimit", "UpperLimit", "Unit", "Value", "Result"]

    return headers, rows
