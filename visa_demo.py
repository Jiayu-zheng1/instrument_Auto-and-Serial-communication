"""VISA 连接 Demo — 扫描资源、连接仪器、查询 *IDN?"""

import pyvisa


def scan_resources():
    """扫描所有可用的 VISA 资源（NI-VISA + pyvisa-py 两个后端）"""
    print("=" * 60)
    print("VISA 资源扫描 Demo")
    print("=" * 60)

    # 1. NI-VISA 后端
    try:
        rm_ni = pyvisa.ResourceManager()
        resources = rm_ni.list_resources()
        print(resources)
        if resources:
            for r in resources:
                print(f"    {r}")
        else:
            print("    (无资源)")
    except Exception as e:
        print(f"    NI-VISA 加载失败: {e}")

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


if __name__ == "__main__":
    scan_resources()
