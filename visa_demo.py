"""VISA 连接 Demo — 扫描资源、连接仪器、查询 *IDN?"""

import pyvisa


# def scan_resources():
#     """扫描所有可用的 VISA 资源（NI-VISA + pyvisa-py 两个后端）"""
#     print("=" * 60)
#     print("VISA 资源扫描 Demo")
#     print("=" * 60)

#     # 1. NI-VISA 后端
#     try:
#         rm_ni = pyvisa.ResourceManager()
#         resources = rm_ni.list_resources()
#         print(resources)
#         if resources:
#             for r in resources:
#                 print(f"    {r}")
#         else:
#             print("    (无资源)")
#     except Exception as e:
#         print(f"    NI-VISA 加载失败: {e}")

# # 2. pyvisa-py 后端
# print("\n[2] pyvisa-py 后端 (@py):")
# try:
#     rm_py = pyvisa.ResourceManager("@py")
#     resources = rm_py.list_resources()
#     if resources:
#         for r in resources:
#             print(f"    {r}")
#     else:
#         print("    (无资源)")
# except Exception as e:
#     print(f"    pyvisa-py 加载失败: {e}")

# return rm_ni if 'rm_ni' in dir() else None


# def connect_and_query(rm, resource_str: str):
#     """连接指定资源并查询 *IDN?"""
#     print(f"\n--- 连接: {resource_str} ---")
#     try:
#         instr = rm.open_resource(resource_str)
#         instr.timeout = 5000
#         instr.read_termination = "\n"
#         idn = instr.query("*IDN?").strip()
#         print(f"    *IDN? => {idn}")
#         instr.close()
#         return idn
#     except Exception as e:
#         print(f"    连接失败: {e}")
#         return None


# if __name__ == "__main__":
#     # scan_resources()

a = "055B13000603006BB02991689832F165423591F7998D90"
print(a[13:-1])


# ═══════════════════════════════════════════════════════════════════════════
#  Bundle Version 解析 (port from Lua API.parseBundleVer)
# ═══════════════════════════════════════════════════════════════════════════


def parse_bundle_ver(ret_hex: str, ret_ascii: str = None):
    """解析 DUT 返回的 hex 响应，提取 Bundle Version。

    Lua API.parseBundleVer 的 hex 解析逻辑：
      1. 跳过前 12 个 hex 字符（6 bytes header: 055A + length + cmd + status）
      2. 校验第 13-14 字符（第 7 byte）必须为 "00"（状态字节）
      3. 跳过状态字节后，将剩余的 hex 按 2 字符一组拆分
      4. 分组：a(2 bytes) / b(8 bytes) / c(2 bytes)
      5. 每组反转（LE→BE），hex→decimal，拼接为版本号

    Args:
        ret_hex:  DUT 返回的原始 hex 字符串，如:
                  "055B13000603006BB02991689832F165423591F7998D90"
        ret_ascii: ASCII 返回值（可选），用于提取 bundleVersionStr

    Returns:
        bundle_version    — 解析出的 Bundle Version，如 "03470734000007455201"
        bundle_version_str — ASCII 中匹配到的版本字符串（如 "1A234"），无匹配时 None
    """
    # 0. 去空格（输入可能是 "055B 1300 0603 006B ..." 格式）
    ret_hex = ret_hex.replace(" ", "").replace("\n", "").replace("\r", "")

    # 1. 跳过 header（前 12 个 hex 字符 = 6 bytes）
    #    Lua: retHex:sub(13, -1)  →  Python: [12:]
    hex_str = ret_hex[12:]

    # 2. 校验第一个字节必须为 "00"
    if hex_str[:2] != "00":
        raise ValueError(f"状态字节异常: 期望 00，实际 {hex_str[:2]}")

    # 3. 跳过状态字节
    hex_str = hex_str[2:]

    # 4. 按 2 字符一组拆分 hex 字节对
    hex_pairs = [hex_str[i : i + 2] for i in range(0, len(hex_str), 2)]

    # 5. 分组：a(索引0-1) / b(索引2-9) / c(索引10-11)
    a_tab = hex_pairs[0:2]  # 2 bytes
    b_tab = hex_pairs[2:10]  # 8 bytes
    c_tab = hex_pairs[10:12]  # 2 bytes

    # 6. 每组反转（Little-Endian → Big-Endian），hex → decimal
    a_val = str(int("".join(reversed(a_tab)), 16))
    b_val = str(int("".join(reversed(b_tab)), 16))
    c_val = str(int("".join(reversed(c_tab)), 16))

    bundle_version = a_val + b_val + c_val

    # 7. 从 ASCII 返回值中提取版本字符串（可选）
    bundle_version_str = None
    if ret_ascii:
        import re

        m = re.search(r"\d\D\d+", str(ret_ascii))
        if m:
            bundle_version_str = m.group()

    return bundle_version, bundle_version_str


if __name__ == "__main__":
    # 测试解析函数
    test_hex = "05 5B 13 00 06 03 00 6B B0 29 91 68 98 32 F1 65 42 35 91 F7 99 8D 90"
    test_ascii = ".[.....k.).h.2.eB5....."
    version, version_str = parse_bundle_ver(test_hex, test_ascii)
    print(f"Bundle Version: {version}, Bundle Version Str: {version_str}")
