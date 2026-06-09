"""Limits.csv 统一加载器 — 单一入口解析 CSV，返回带已解析 config 的行。

用法:
    from app.utils.limits_loader import load_limits_csv
    csv_data = load_limits_csv()
    # csv_data = [{"TestItem": ..., "TestName": ..., ..., "config": {...}}, ...]
"""

import os
from app.utils.constants import LIMITS_CSV
from app.utils.config_parser import parse_config


def load_limits_csv() -> list[dict]:
    """加载并解析 Limits.csv，返回 dict 列表（config 字段已解析为 dict）。"""
    if not os.path.exists(LIMITS_CSV):
        return []

    with open(LIMITS_CSV, "r", encoding="utf-8") as f:
        lines = f.readlines()

    if not lines:
        return []

    headers = [h.strip() for h in lines[0].split(",")]
    rows = []
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split(",", 8)  # 前 8 列用逗号分，第 9 列取剩余部分
        if len(parts) < 9:
            parts.extend([""] * (9 - len(parts)))

        row = {}
        for i, header in enumerate(headers[:8]):
            row[header] = parts[i].strip() if i < len(parts) else ""

        config_text = parts[8].strip().rstrip(",") if len(parts) > 8 else ""
        row["config"] = parse_config(config_text)
        rows.append(row)

    return rows
