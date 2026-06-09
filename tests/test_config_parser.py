"""config_parser 单元测试 — 覆盖旧格式、新格式（Atlas2 风格）、边界情况。"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app.utils.config_parser import parse_config


# ── 空/None 输入 ──

def test_empty_string():
    assert parse_config("") == {}

def test_none_input():
    assert parse_config(None) == {}

def test_already_dict_passthrough():
    d = {"hex_cmd": "055A..."}
    assert parse_config(d) is d


# ── 旧格式兼容 — dict literal ──

def test_legacy_hex_cmd_only():
    result = parse_config("('hex_cmd':'055a060010804d4c42230D0A')")
    assert result == {"hex_cmd": "055a060010804d4c42230D0A"}

def test_legacy_hex_cmd_with_regex():
    result = parse_config(
        "('hex_cmd':'055A1200920F41542B454155584144433D312C310D0A',"
        "'regex':'hw_id\\s\\W\\s(\\w+)','group':'1','delay':'1')"
    )
    assert result["hex_cmd"].startswith("055A")
    assert result["regex"] == 'hw_id\\s\\W\\s(\\w+)'
    assert result["group"] == "1"
    assert result["delay"] == "1"

def test_legacy_json_format():
    result = parse_config('{"hex_cmd": "055A02000c800D0A"}')
    assert result == {"hex_cmd": "055A02000c800D0A"}

def test_legacy_missing_closing_paren():
    result = parse_config("('hex_cmd':'055A...','regex':'pat','group':'1'")
    assert result["hex_cmd"] == "055A..."
    assert result["regex"] == "pat"
    assert result["group"] == "1"


# ── 新格式 — Atlas2 风格：action arg1 arg2... ──

def test_new_hex_cmd_only():
    result = parse_config("hex_cmd 055A02000c800D0A")
    assert result == {"action": "hex_cmd", "args": ["055A02000c800D0A"]}

def test_new_hex_cmd_with_all_params():
    result = parse_config(r"hex_cmd 055A... hw_id\s\W\s(\w+) 1 1")
    assert result["action"] == "hex_cmd"
    assert result["args"] == [r"055A...", r"hw_id\s\W\s(\w+)", "1", "1"]

def test_new_hex_cmd_with_regex_only():
    result = parse_config(r"hex_cmd 055A... hw_id\s\W\s(\w+)")
    assert result["args"] == [r"055A...", r"hw_id\s\W\s(\w+)"]

def test_new_connect():
    result = parse_config("connect")
    assert result == {"action": "connect", "args": []}

def test_new_connect_with_extra():
    # 多余 token 忽略由 handler 处理
    result = parse_config("connect extra stuff")
    assert result["action"] == "connect"
    assert result["args"] == ["extra", "stuff"]

def test_new_quoted_regex_with_spaces():
    result = parse_config('hex_cmd 055A... "regex with spaces" 1')
    assert result["args"] == ["055A...", "regex with spaces", "1"]

def test_new_single_arg():
    result = parse_config("relay_ON 3")
    assert result == {"action": "relay_ON", "args": ["3"]}

def test_new_no_args():
    result = parse_config("relay_on_all")
    assert result == {"action": "relay_on_all", "args": []}

def test_new_multiple_args():
    result = parse_config("ps_output_on 1 3.3 0.5")
    assert result == {"action": "ps_output_on", "args": ["1", "3.3", "0.5"]}


# ── 边界情况 ──

def test_unmatched_quotes_fallback():
    result = parse_config('hex_cmd 055A... "unclosed quote')
    # 引号未闭合 → 视为普通字符
    assert result["action"] == "hex_cmd"
    assert len(result["args"]) >= 1

def test_only_action():
    result = parse_config("relay_on_all")
    assert result == {"action": "relay_on_all", "args": []}

def test_extra_whitespace():
    result = parse_config("  hex_cmd   055A...   1  ")
    assert result["action"] == "hex_cmd"
    assert result["args"] == ["055A...", "1"]


# ── 实际 Limits.csv 数据兼容性 ──

def test_real_csv_row_mlb_sn():
    """Read_MLB_SN — 纯 hex_cmd，无 regex"""
    result = parse_config("('hex_cmd':'055a060010804d4c42230D0A')")
    assert result["hex_cmd"] == "055a060010804d4c42230D0A"

def test_real_csv_row_dut_hwid():
    """ReadDUTHWID — hex_cmd + regex + group + delay"""
    result = parse_config(
        "('hex_cmd':'055A1200920F41542B454155584144433D312C310D0A',"
        "'regex':'hw_id\\s\\W\\s(\\w+)','group':'1','delay':'1')"
    )
    assert result["delay"] == "1"
    assert result["group"] == "1"

def test_real_csv_row_check_fuse():
    """Check_Fuse"""
    result = parse_config("('hex_cmd':'055a02000c800D0A')")
    assert result["hex_cmd"] == "055a02000c800D0A"
