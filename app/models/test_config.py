"""Test configuration model — CSV row parsing and validation."""
import json
import ast
from loguru import logger


class TestConfig:
    """Parsed state from a Limits.csv row."""

    def __init__(self, test_item: str, lower_limit: str, upper_limit: str, config: dict):
        self.test_item = test_item
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
        特殊 limit：No Empty 检查 value 非空，PASSED/ON/True 自动通过。
        数值 limit：统一转 float 做 <= 比较。
        """
        if self.is_special_limit():
            specials = {self.lower_limit_raw, self.upper_limit_raw}
            if "No Empty" in specials or "Empty" in specials:
                ok = bool(value)
                return ok, "Pass" if ok else "Fail"
            # PASSED / ON / True → 自动通过
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
            lower_limit=row.get("LowerLimit", ""),
            upper_limit=row.get("UpperLimit", ""),
            config=_parse_config_text(row.get("config", "") or row.get("Config", "")),
        ))
    return configs


def _parse_config_text(config_text: str) -> dict:
    if not config_text:
        return {}
    try:
        return json.loads(config_text)
    except Exception:
        try:
            return ast.literal_eval(config_text)
        except Exception as e:
            logger.info(f"Error parsing config {config_text}: {e}")
            return {}


def _limit_format(limit: str):
    if limit in ("No Empty", "Empty", "True", "PASSED", "ON"):
        return limit
    if limit.startswith("0x"):
        return limit
    try:
        return int(limit)
    except (ValueError, TypeError):
        return limit
