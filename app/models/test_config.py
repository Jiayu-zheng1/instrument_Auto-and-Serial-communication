"""Test configuration model — CSV row parsing and validation."""
import json
import ast
from loguru import logger


class TestConfig:
    """Parsed state from a Limits.csv row."""

    def __init__(self, test_item: str, test_name: str, lower_limit: str, upper_limit: str, config: dict):
        self.test_item = test_item      # 表格显示名
        self.test_name = test_name      # TestItem 方法名
        self.lower_limit_raw = lower_limit
        self.upper_limit_raw = upper_limit
        self.config = config

    @property
    def lower_limit(self):
        return _limit_format(self.lower_limit_raw)

    @property
    def upper_limit(self):
        return _limit_format(self.upper_limit_raw)

    def is_special_limit(self):
        specials = {"No Empty", "Empty", "True", "ON", "PASSED"}
        return self.lower_limit_raw in specials or self.upper_limit_raw in specials

    def evaluate(self, value) -> tuple[bool, str]:
        """判定 value 是否在 limit 范围内。

        返回 (是否通过, Pass/Fail 标签)。
        特殊 limit：
        - No Empty：检查 value 非空
        - PASSED/ON/True：检查是否有失败标志（FAILED/False/None）
        数值 limit：统一转 float 做 <= 比较。
        """
        if self.is_special_limit():
            specials = {self.lower_limit_raw, self.upper_limit_raw}
            if "No Empty" in specials or "Empty" in specials:
                ok = bool(value)
                return ok, "Pass" if ok else "Fail"
            # PASSED / ON / True → 检查是否有失败标志
            if value is None:
                return False, "Fail"
            # 显式失败标志
            value_str = str(value).strip().upper()
            if value_str in ("FAILED", "FAIL", "ERROR", "FALSE", "0"):
                return False, "Fail"
            # 布尔值 False
            if value is False:
                return False, "Fail"
            # 其他情况（包括原始响应、PASSED、True 等）视为 Pass
            return True, "Pass"

        # 数值比较：统一转 float
        try:
            val = float(value)
            lo = float(self.lower_limit)
            hi = float(self.upper_limit)
            passed = lo <= val <= hi
            return passed, "Pass" if passed else "Fail"
        except (ValueError, TypeError):
            return False, "Fail"


def load_test_configs(csv_rows: list[dict]) -> list[TestConfig]:
    """Parse CSV rows into TestConfig list, filtering Running='Y'."""
    configs = []
    for row in csv_rows:
        if row.get("Running", "") != "Y":
            continue
        configs.append(TestConfig(
            test_item=row.get("TestItem", ""),
            test_name=row.get("TestName", "") or row.get("TestItem", ""),
            lower_limit=row.get("LowerLimit", ""),
            upper_limit=row.get("UpperLimit", ""),
            config=_parse_config_text(row.get("config", "") or row.get("Config", "")),
        ))
    return configs


def _parse_config_text(config_text: str) -> dict:
    if not config_text:
        return {}

    # 尝试 JSON 解析
    try:
        return json.loads(config_text)
    except Exception:
        pass

    # 预处理: CSV 中的 ('key':'val') 格式 -> {'key':'val'}
    text = config_text.strip()
    if text.startswith("(") and text.endswith(")"):
        text = "{" + text[1:-1] + "}"

    try:
        return ast.literal_eval(text)
    except Exception:
        pass

    # 手动解析: 支持 ('key':'val','key2':'val2') 格式
    return _manual_parse_config(config_text)


def _manual_parse_config(config_text: str) -> dict:
    """手动解析配置字符串，支持 ('key':'val','key2':'val2') 格式。"""
    result = {}
    text = config_text.strip()

    # 去掉外层括号
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1]
    elif text.startswith("("):
        text = text[1:]
    elif text.endswith(")"):
        text = text[:-1]

    if not text:
        return result

    # 解析 'key':'val' 对
    import re
    pattern = r"'([^']+)'\s*:\s*'([^']*)'"
    matches = re.findall(pattern, text)
    for key, value in matches:
        result[key] = value

    if not result:
        logger.info(f"Error parsing config {config_text}: no key-value pairs found")

    return result


def _limit_format(limit: str):
    if limit in ("No Empty", "Empty", "True", "PASSED", "ON"):
        return limit
    if limit.startswith("0x"):
        return limit
    try:
        return int(limit)
    except (ValueError, TypeError):
        return limit
