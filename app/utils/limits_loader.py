"""Limits.csv 统一加载器 — 单一入口解析 CSV，返回带已解析 config 的行。

用法:
    from app.utils.limits_loader import load_limits_csv
    csv_data = load_limits_csv()
    # csv_data = [{"TestItem": ..., "TestName": ..., ..., "config": {...}}, ...]
"""

import os
import json
import ast
import re
from app.utils.constants import LIMITS_CSV


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
        row["config"] = _parse_config(config_text)
        rows.append(row)

    return rows


def _parse_config(text: str) -> dict:
    """解析 config 列文本为 dict。"""
    if not text:
        return {}

    # JSON
    try:
        return json.loads(text)
    except Exception:
        pass

    # ('key':'val') -> {'key':'val'} + ast.literal_eval
    t = text.strip()
    if t.startswith("(") and t.endswith(")"):
        t = "{" + t[1:-1] + "}"
    try:
        return ast.literal_eval(t)
    except Exception:
        pass

    # 手动正则
    result = {}
    t2 = text.strip()
    if t2.startswith("(") and t2.endswith(")"):
        t2 = t2[1:-1]
    elif t2.startswith("("):
        t2 = t2[1:]
    elif t2.endswith(")"):
        t2 = t2[:-1]

    if t2:
        for m in re.findall(r"'([^']+)'\s*:\s*'([^']*)'", t2):
            result[m[0]] = m[1]

    return result
