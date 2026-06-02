"""Test item business logic — DUT 通信 + 仪器读取控制。"""

import re
import time
import subprocess as sub
from app.utils.logger import get_logger

logger = get_logger("DUT")
from app.models.device import Device, get_ports

verRex = re.compile(r"Application\s\W\d\d\W\S\s(\w*)")
uvpRex = re.compile(r"Reset Count:\s(\d+)")
socRex = re.compile(
    r"\- 0x([0-9a-f]{2}) 0x([0-9a-f]{2})[\s\S]+0x([0-9a-f]{2}) 0x[0-9a-f]{2}"
)
btRex = re.compile(r"NRF (\w*)\s*\w*\s(\w*)\W*\w*\s(\w*)")
AquilaRex = re.compile(r"chip\w\w=(\Sx\S\S)\S*")
fgsnRex = re.compile(r"\| (\S*)")
hwidRex = re.compile(r"HW (\w*) -")
valtageRex = re.compile(r"voltageCalibrated : (\w*) mV")
temperatureRex = re.compile(r"temperature : (\w*\W\w) C")
lockVerRex = re.compile(r"0000\W:(\S\S)")


class TestItem:
    """Encapsulates all DUT test procedures."""

    def __init__(self, instrument_manager=None):
        self.FGSN = None
        self.dut = None
        self.ScanSN = None
        self._scan_cache: dict[str, dict[str, float]] = {}
        self._mgr = instrument_manager  # 由调用方注入

    def connent_dut(self, timeout=5):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                ports = get_ports()
                dut = Device()
                dut.open_get_port(port=ports[0].device, baudrate=921600)
                if dut.ser and dut.ser.is_open:
                    logger.info("====DUT connection is successful=====")
                    self.dut = dut
                    return True
            except Exception as e:
                logger.info("open serial Fail")
            time.sleep(0.1)
        logger.info("连接超时")
        return False

    def close_dut(self):
        if self.dut is not None:
            self.dut.close_port()
            logger.info("DUT has been shut down ")
            self.dut = None

    def Info_CheckDUT(self):
        if self.dut is None:
            self.connent_dut()
            if self.dut:
                return True
            else:
                logger.info("DUT connection Fail")
                return False

    def run_read_cmd(self, method_name, config):
        """按 config 执行测试，method_name 为 TestName（匹配 TestItem 方法）。
        返回 (raw_hex, ascii_str, result) 元组。
        """
        action = config.get("action", "")
        if action == "method":
            target = config.get("method") or method_name
            return "", "", getattr(self, target)()
        if action == "connect":
            return "", "", "PASSED" if self.connent_dut() else "FAILED"

        # DUT 未连接时直接返回空值，不 crash
        if self.dut is None:
            logger.info(f"{method_name}: DUT 未连接，返回 None")
            return "", "", None

        for cmd in self._as_list(config.get("pre_cmds")):
            self.dut.send_cmd(cmd)

        hex_cmd = config.get("hex_cmd")
        if hex_cmd:
            delay = float(config.get("delay", 0.05))
            raw_hex, data = self.dut.send_hex_cmd(hex_cmd, delay=delay)
            logger.info(f"{method_name} raw response: {data}")
        else:
            cmd = (
                config.get("cmd") or config.get("command") or config.get("instruction")
            )
            data = self.dut.read_Write(cmd) if cmd else ""
            raw_hex = ""

        result = self._extract_config_value(data, config)

        for attr in self._as_list(config.get("set_attr")):
            setattr(self, attr, result)

        for cmd in self._as_list(config.get("post_cmds")):
            self.dut.send_cmd(cmd)

        logger.info(f"{method_name} config result: {result}")
        return raw_hex, data, result

    def _extract_config_value(self, data, config):
        if data is None:
            return None

        contains = config.get("contains")
        if contains:
            pass_value = config.get("pass_value", "PASSED")
            fail_value = config.get("fail_value", "FAILED")
            return pass_value if str(contains) in data else fail_value

        regex = config.get("regex")
        if not regex:
            return self._format_config_value(data, config)

        matches = list(re.finditer(regex, data, re.S))
        if not matches:
            logger.info(f"regex no match: {regex}")
            return config.get("default")

        match_index = int(config.get("match_index", config.get("index", 0)))
        match = matches[match_index]
        groups = config.get("group")
        if groups:
            if isinstance(groups, list):
                value = [match.group(int(group)) for group in groups]
            else:
                value = match.group(int(groups))
        else:
            group = int(config.get("group", config.get("position", 1)))
            value = match.group(group)
        return self._format_config_value(value, config)

    def _format_config_value(self, value, config):
        if isinstance(value, str) and config.get("strip", True):
            value = value.strip()

        cast = config.get("cast", "str")
        if cast == "int":
            return int(value)
        if cast == "float":
            return float(value)
        if cast == "hex_int":
            return int(value, 16)
        return value

    def _as_list(self, value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        return [value]

    # ── 原有 DUT 方法 ────────────────────────────────────────────────

    def Check_FGSN(self):
        fgsn = ""
        cmd = "ds get -s SERIAL_FG"
        data = self.dut.read_Write(cmd)
        logger.info(f"Check_FGSN raw response: {data}")
        if data:
            value = fgsnRex.search(data)
            fgsn = value.group(1)
            if fgsn:
                self.FGSN = fgsn
                if self.FGSN == self.ScanSN:
                    return True
                else:
                    return False
            else:
                logger.info("FGSN is None")
                return False

    def MCU_FW_Ver(self):
        cmd = "sys version"
        data = self.dut.read_Write(cmd)
        logger.info(f"MCU_FW_Ver raw response: {data}")
        if data:
            value = verRex.search(data)
            return value.group(1)
        return None

    def Info_UVPCheck(self):
        cmd = "stylus stats"
        data = self.dut.read_Write(cmd)
        logger.info(f"Info_UVPCheck raw response: {data}")
        if data:
            uvpver = uvpRex.search(data).group(1)
            return uvpver
        return None

    def Info_SOC(self):
        cmd = "hid -i 0 get 0x21"
        data1 = self.dut.read_Write(cmd)
        logger.info(f"Info_SOC raw response: {data1}")
        if data1:
            socver = int(socRex.search(data1).group(3), 16)
            return socver
        return None

    def BT_FW_Ver(self):
        cmd = "bt version"
        data = self.dut.read_Write(cmd)
        logger.info(f"BT_FW_Ver raw response: {data}")
        if data:
            N = btRex.search(data).group(1)
            A = btRex.search(data).group(2)
            bt_fwver = btRex.search(data).group(3)
            if N == A == bt_fwver:
                return f"v{bt_fwver}"
            else:
                logger.info(f"BRF:{N},AFU:{A},FW:{bt_fwver}")
                return None

    def CheckAquilaID(self):
        self.dut.read_Write("power stim on")
        data = self.dut.read_Write("stim rev")
        logger.info(f"CheckAquilaID raw response: {data}")
        if data:
            return AquilaRex.search(data).group(1)
        else:
            logger.info("AquilaID is None")
            return None

    def Check_HWID(self):
        cmd = "sys banner"
        data = self.dut.read_Write(cmd)
        logger.info(f"Check_HWID raw response: {data}")
        if data:
            return hwidRex.search(data).group(1)
        else:
            logger.info("HWID is None")
            return None

    def Read_Voltage(self):
        cmd = "pmu status"
        data = self.dut.read_Write(cmd)
        logger.info(f"Read_Voltage raw response: {data}")
        if data:
            return valtageRex.search(data).group(1)
        else:
            logger.info("voltage is None")
            return None

    def Read_Temperature(self):
        cmd = "pmu status"
        data = self.dut.read_Write(cmd)
        logger.info(f"Read_Temperature raw response: {data}")
        if data:
            return temperatureRex.search(data).group(1)
        else:
            logger.info("temperature is None")
            return None

    def Set_Lock(self):
        self.dut.send_cmd("ds clear -s PMU_CHARGE_ON_PLUG")
        self.dut.send_cmd("ds get 0")
        self.dut.read_Write("ds set 0 1")
        self.dut.send_cmd("sys reset")
        time.sleep(5)
        cmd = "ls /dev/cu.*"
        p = sub.Popen(cmd, shell=True, stdout=sub.PIPE, stderr=sub.PIPE)
        p.communicate()
        self.connent_dut()
        if self.dut:
            self.dut.read_Write("help")
            logger.info("Set Lock PASSED")
            return True
        else:
            logger.info("not find DUT")
            return False

    def Check_Lock(self):
        result = self.dut.read_Write("ds get -s LOCK")
        logger.info(f"Check_Lock raw response: {result}")
        lockVerMo = lockVerRex.search(result).group(1)
        logger.info(f"LockVer:{lockVerMo}")
        if lockVerMo:
            if lockVerMo == "01":
                return lockVerMo
            else:
                return "00"
        else:
            logger.info("LockVer is None")
            return "None"

    def FinishSetting(self):
        result = self.dut.read_Write("stylus uvp")
        logger.info(f"FinishSetting raw response: {result}")
        if "UVP mode" in result:
            logger.info("Finish Setting PASSED")
            return True
        else:
            logger.info("Finish Setting FAILED")
            return False

    # ═══════════════════════════════════════════════════════════════════════
    #  仪器访问层 — _mgr 由构造函数注入
    # ═══════════════════════════════════════════════════════════════════════

    @property
    def _dmm(self):
        return self._mgr.dmm

    @property
    def _ps(self):
        return self._mgr.ps

    @property
    def _relay(self):
        return self._mgr.relay

    @property
    def _dmm_ok(self) -> bool:
        return self._mgr.dmm_connected

    @property
    def _ps_ok(self) -> bool:
        return self._mgr.ps_connected

    @property
    def _relay_ok(self) -> bool:
        return self._mgr.relay_connected

    # ═══════════════════════════════════════════════════════════════════════
    #  批量扫描 — 数据存入 _scan_cache，供后续独立测量方法读取
    # ═══════════════════════════════════════════════════════════════════════

    def scan_resistance_slot1(self):
        """批量扫描 Slot 1 (101–120) 电阻值，结果缓存到 _scan_cache['resistance']"""
        if not self._dmm_ok:
            logger.info("34970A 未连接，无法扫描电阻")
            return "FAILED"
        channels = ",".join(str(i) for i in range(101, 121))
        result = self._dmm.scan_slot_res(channels)
        if result is None:
            logger.info("scan_resistance slot1 返回 None")
            return "FAILED"
        self._scan_cache["resistance"] = {str(k): v for k, v in result.items()}
        logger.info(f"slot1 电阻扫描完成: {len(self._scan_cache['resistance'])} 个通道")
        return "PASSED"

    def scan_resistance_slot2(self):
        """批量扫描 Slot 2 (201–217) 电阻值，合并到 _scan_cache['resistance']"""
        if not self._dmm_ok:
            logger.info("34970A 未连接，无法扫描电阻")
            return "FAILED"
        channels = ",".join(str(i) for i in range(201, 218))
        result = self._dmm.scan_slot_res(channels)
        if result is None:
            logger.info("scan_resistance slot2 返回 None")
            return "FAILED"
        cache = self._scan_cache.setdefault("resistance", {})
        cache.update({str(k): v for k, v in result.items()})
        logger.info(f"slot2 电阻扫描完成: {len(result)} 个通道")
        return "PASSED"

    def scan_voltage(self):
        """批量扫描 Slot 1 (101–109) 直流电压 (mV)，结果缓存到 _scan_cache['voltage']"""
        if not self._dmm_ok:
            logger.info("34970A 未连接，无法扫描电压")
            return "FAILED"
        channels = ",".join(str(i) for i in range(101, 110))
        result = self._dmm.scan_slot_dcv(channels, unit="mV")
        if result is None:
            logger.info("scan_voltage 返回 None")
            return "FAILED"
        self._scan_cache["voltage"] = {str(k): v for k, v in result.items()}
        logger.info(f"电压扫描完成: {len(self._scan_cache['voltage'])} 个通道")
        return "PASSED"

    # ═══════════════════════════════════════════════════════════════════════
    #  Slot 1 电阻独立测量 (101–120)
    # ═══════════════════════════════════════════════════════════════════════

    def _get_resistance(self, channel: str):
        """直接通过 DMM 测量单通道阻抗（MEAS:RES? 一键完成，不走缓存）。"""
        dmm = self._dmm
        if dmm is None:
            logger.info(f"DMM 未连接，ch{channel} 返回 -9999")
            return "-9999"
        val = dmm.measure_res(int(channel))
        logger.info(f"[RAW] 阻抗 ch{channel} = {val} Ω")
        return val

    def Measure_Impedance_PP_VBUS_USBC_To_GND(self):
        return self._get_resistance("101")

    def Measure_Impedance_PP_VBUS_RVP_To_GND(self):
        return self._get_resistance("102")

    def Measure_Impedance_PP_VBUS_OUT_To_GND(self):
        return self._get_resistance("103")

    def Measure_Impedance_PP_VBUS_CONN_To_GND(self):
        return self._get_resistance("104")

    def Measure_Impedance_PP_VBATP_CON_To_GND(self):
        return self._get_resistance("105")

    def Measure_Impedance_PP1V2_BUCK_OUT_To_GND(self):
        return self._get_resistance("106")

    def Measure_Impedance_PP_PMID_CHG_To_GND(self):
        return self._get_resistance("107")

    def Measure_Impedance_PP_VSYS_CHG_To_GND(self):
        return self._get_resistance("108")

    def Measure_Impedance_PP_CHG_REGN_LDO_To_GND(self):
        return self._get_resistance("109")

    def Measure_Impedance_PP_VBUS_HB_To_GND(self):
        return self._get_resistance("110")

    def Measure_Impedance_PP1V8_SUR_TON_RIGHT_To_GND(self):
        return self._get_resistance("111")

    def Measure_Impedance_PP1V8_SUR_TON_LEFT_To_GND(self):
        return self._get_resistance("112")

    def Measure_Impedance_PP_LP5811_BOOST_To_GND(self):
        return self._get_resistance("113")

    def Measure_Impedance_PP_VCHG_IN_To_GND(self):
        return self._get_resistance("114")

    def Measure_Impedance_PP_VBAT_To_GND(self):
        return self._get_resistance("115")

    def Measure_Impedance_PP_VSYS_To_GND(self):
        return self._get_resistance("116")

    def Measure_Impedance_PP_VAUD_To_GND(self):
        return self._get_resistance("117")

    def Measure_Impedance_PP1V8_VIO_To_GND(self):
        return self._get_resistance("118")

    def Measure_Impedance_PP1V8_VDIG18_To_GND(self):
        return self._get_resistance("119")

    def Measure_Impedance_PP3V1_VDD31_To_GND(self):
        return self._get_resistance("120")

    # ═══════════════════════════════════════════════════════════════════════
    #  Slot 2 电阻独立测量 (201–217)
    # ═══════════════════════════════════════════════════════════════════════

    def Measure_Impedance_PP1V8_VA18_To_GND(self):
        return self._get_resistance("201")

    def Measure_Impedance_PP_VPA_To_GND(self):
        return self._get_resistance("202")

    def Measure_Impedance_PP_DVDD_MLDO_To_GND(self):
        return self._get_resistance("203")

    def Measure_Impedance_FSOURCE_D_To_GND(self):
        return self._get_resistance("204")

    def Measure_Impedance_PP_VOX_CLK_To_GND(self):
        return self._get_resistance("205")

    def Measure_Impedance_PP_VOX_DAT_To_GND(self):
        return self._get_resistance("206")

    def Measure_Impedance_PDM_CLK_FF1_FB_To_GND(self):
        return self._get_resistance("207")

    def Measure_Impedance_PDM_DAT_FF1_FB_To_GND(self):
        return self._get_resistance("208")

    def Measure_Impedance_PDM_CLK_FF2_FF3_To_GND(self):
        return self._get_resistance("209")

    def Measure_Impedance_PDM_DAT_FF2_FF3_To_GND(self):
        return self._get_resistance("210")

    def Measure_Impedance_PP_VDD_To_GND(self):
        return self._get_resistance("211")

    def Measure_Impedance_CC1_To_GND(self):
        return self._get_resistance("212")

    def Measure_Impedance_CC2_To_GND(self):
        return self._get_resistance("213")

    def Measure_Impedance_PP_VCORE_To_GND(self):
        return self._get_resistance("214")

    def Measure_Impedance_PP_VRF_IN_To_GND(self):
        return self._get_resistance("215")

    def Measure_Impedance_PP_VRTC_To_GND(self):
        return self._get_resistance("216")

    def Measure_Impedance_PP_VSRAM_To_GND(self):
        return self._get_resistance("217")

    # ═══════════════════════════════════════════════════════════════════════
    #  电压独立测量 (101–109)
    # ═══════════════════════════════════════════════════════════════════════

    def _get_voltage(self, channel: str):
        """直接通过 DMM 测量单通道直流电压 (mV)（不走缓存）。"""
        dmm = self._dmm
        if dmm is None:
            logger.info(f"DMM 未连接，ch{channel} 返回 -9999")
            return "-9999"
        val = dmm.measure_dcv(int(channel), unit="mV")
        if val is not None:
            logger.info(f"[RAW] 电压 ch{channel} = {val} mV")
            return str(val)
        return "-9999"

    def Measure_Voltage_PP_VBUS_USBC_To_GND(self):
        return self._get_voltage("101")

    def Measure_Voltage_PP_VBUS_RVP_To_GND(self):
        return self._get_voltage("102")

    def Measure_Voltage_PP_VBUS_OUT_To_GND(self):
        return self._get_voltage("103")

    def Measure_Voltage_PP_VBUS_CONN_To_GND(self):
        return self._get_voltage("104")

    def Measure_Voltage_PP_VBAT_CON_To_GND(self):
        return self._get_voltage("105")

    def Measure_Voltage_PP1V2_BUCK_OUT_To_GND(self):
        return self._get_voltage("106")

    def Measure_Voltage_PP_PMID_CHG_To_GND(self):
        return self._get_voltage("107")

    def Measure_Voltage_PP_VSYS_CHG_To_GND(self):
        return self._get_voltage("108")

    def Measure_Voltage_PP_CHG_REGN_LDO_To_GND(self):
        return self._get_voltage("109")

    def Measure_Voltage_PP_VBUS_HB_To_GND(self):
        return self._get_voltage("110")

    def Measure_Voltage_PP1V8_SUR_TON_RIGHT_To_GND(self):
        return self._get_voltage("111")

    def Measure_Voltage_PP1V8_SUR_TON_LEFT_To_GND(self):
        return self._get_voltage("112")

    def Measure_Voltage_PP_LP5811_BOOST_To_GND(self):
        return self._get_voltage("113")

    def Measure_Voltage_PP_VCHG_IN_To_GND(self):
        return self._get_voltage("114")

    def Measure_Voltage_PP_VBAT_To_GND(self):
        return self._get_voltage("115")

    def Measure_Voltage_PP_VSYS_To_GND(self):
        return self._get_voltage("116")

    def Measure_Voltage_PP_VAUD_To_GND(self):
        return self._get_voltage("117")

    def Measure_Voltage_PP1V8_VIO_To_GND(self):
        return self._get_voltage("118")

    def Measure_Voltage_PP1V8_VDIG18_To_GND(self):
        return self._get_voltage("119")

    def Measure_Voltage_PP3V1_VDD31_To_GND(self):
        return self._get_voltage("120")

    def Measure_Voltage_PP1V8_VA18_To_GND(self):
        return self._get_voltage("201")

    def Measure_Voltage_PP_VPA_To_GND(self):
        return self._get_voltage("202")

    def Measure_Voltage_PP_DVDD_MLDO_To_GND(self):
        return self._get_voltage("203")

    def Measure_Voltage_FSOURCE_D_To_GND(self):
        return self._get_voltage("204")

    def Measure_Voltage_PP_VOX_CLK_To_GND(self):
        return self._get_voltage("205")

    def Measure_Voltage_PP_VOX_DAT_To_GND(self):
        return self._get_voltage("206")

    def Measure_Voltage_PDM_CLK_FF1_FB_To_GND(self):
        return self._get_voltage("207")

    def Measure_Voltage_PDM_DAT_FF1_FB_To_GND(self):
        return self._get_voltage("208")

    def Measure_Voltage_PDM_CLK_FF2_FF3_To_GND(self):
        return self._get_voltage("209")

    def Measure_Voltage_PDM_DAT_FF2_FF3_To_GND(self):
        return self._get_voltage("210")

    def Measure_Voltage_PP_VDD_To_GND(self):
        return self._get_voltage("211")

    def Measure_Voltage_CC1_To_GND(self):
        return self._get_voltage("212")

    def Measure_Voltage_CC2_To_GND(self):
        return self._get_voltage("213")

    def Measure_Voltage_PP_VCORE_To_GND(self):
        return self._get_voltage("214")

    def Measure_Voltage_PP_VRF_IN_To_GND(self):
        return self._get_voltage("215")

    def Measure_Voltage_PP_VRTC_To_GND(self):
        return self._get_voltage("216")

    def Measure_Voltage_PP_VSRAM_To_GND(self):
        return self._get_voltage("217")

    # ═══════════════════════════════════════════════════════════════════════
    #  单点电压测量 — 不经批量扫描，直接读 DMM
    # ═══════════════════════════════════════════════════════════════════════

    def Measure_Voltage_PP1V8_SUR_RST_LEFT_To_GND(self):
        """单点测量通道 112 直流电压 (mV)"""
        if not self._dmm_ok:
            return "-9999"
        val = self._dmm.measure_dcv(112, unit="mV")
        return str(val) if val is not None else "-9999"

    def Measure_Voltage_PP_VBUS_HB_To_GND(self):
        """单点测量通道 110 直流电压 (mV)"""
        if not self._dmm_ok:
            return "-9999"
        val = self._dmm.measure_dcv(110, unit="mV")
        return str(val) if val is not None else "-9999"

    def Measure_Voltage_PP_LP5811_BOOST_To_GND(self):
        """单点测量通道 113 直流电压 (mV)"""
        if not self._dmm_ok:
            return "-9999"
        val = self._dmm.measure_dcv(113, unit="mV")
        return str(val) if val is not None else "-9999"

    # ═══════════════════════════════════════════════════════════════════════
    #  继电器控制
    # ═══════════════════════════════════════════════════════════════════════

    def relay_ON(self, channel: int):
        """闭合指定继电器通道 (1–8)"""
        if not self._relay_ok:
            logger.info("Relayboard 未连接")
            return "FAILED"
        self._relay.relay_ON(channel)
        return "PASSED"

    def relay_OFF(self, channel: int):
        """断开指定继电器通道 (1–8)"""
        if not self._relay_ok:
            logger.info("Relayboard 未连接")
            return "FAILED"
        self._relay.relay_OFF(channel)
        return "PASSED"

    def relay_on_range(self, start: int, end: int):
        """闭合指定范围继电器 (含两端)"""
        if not self._relay_ok:
            logger.info("Relayboard 未连接")
            return "FAILED"
        self._relay.turn_on_relays(range(start, end + 1))
        return "PASSED"

    def relay_off_range(self, start: int, end: int):
        """断开指定范围继电器 (含两端)"""
        if not self._relay_ok:
            logger.info("Relayboard 未连接")
            return "FAILED"
        self._relay.turn_off_relays(range(start, end + 1))
        return "PASSED"

    def relay_on_all(self):
        """闭合全部 8 路继电器"""
        return self.relay_on_range(1, 8)

    def relay_off_all(self):
        """断开全部 8 路继电器"""
        return self.relay_off_range(1, 8)

    # ═══════════════════════════════════════════════════════════════════════
    #  程控电源 IT6382
    # ═══════════════════════════════════════════════════════════════════════

    def ps_output_on_all(
        self,
        vol1: float = 0,
        vol2: float = 0,
        vol3: float = 0,
        curr1: float = 0,
        curr2: float = 0,
        curr3: float = 0,
    ):
        """三通道同时输出。参数: CH1/CH2/CH3 电压(V) + 电流(A)"""
        if not self._ps_ok:
            logger.info("IT6382 未连接")
            return "FAILED"
        self._ps.output_on_all(vol1, vol2, vol3, curr1, curr2, curr3)
        return "PASSED"

    def ps_output_off_all(self):
        """三通道同时关闭"""
        if not self._ps_ok:
            logger.info("IT6382 未连接")
            return "FAILED"
        self._ps.output_off_all()
        return "PASSED"

    def ps_output_on(self, channel: int, vol: float, curr: float):
        """单通道输出。channel: 1/2/3"""
        if not self._ps_ok:
            logger.info("IT6382 未连接")
            return "FAILED"
        self._ps.output_on(channel, vol, curr)
        return "PASSED"

    def ps_output_off(self, channel: int):
        """单通道关闭"""
        if not self._ps_ok:
            logger.info("IT6382 未连接")
            return "FAILED"
        self._ps.output_off(channel)
        return "PASSED"

    def ps_read_voltage(self, channel: int):
        """读取指定通道电压 (mV)"""
        if not self._ps_ok:
            return "-9999"
        return self._ps.read_voltage(channel)

    def ps_read_current(self, channel: int):
        """读取指定通道电流 (mA)"""
        if not self._ps_ok:
            return "-9999"
        return self._ps.read_current(channel)

    # ═══════════════════════════════════════════════════════════════════════
    #  DUT Info 测试方法
    # ═══════════════════════════════════════════════════════════════════════

    def Enable_HWID(self):
        """启用 HWID 显示（某些机型默认隐藏）"""
        if self.dut is None:
            logger.info("DUT 未连接，无法启用 HWID")
            return "FAILED"
        hex_data, ASCII_data = self.dut.send_hex_cmd(
            "055A2600920F41542B454750494F3D4750494F5F5345545F414C4C3A33392C302C312C312C322C300D0A",
            delay=0.05,
        )
        logger.info(f"Enable_HWID raw response: {ASCII_data}")
        if "di=1" in ASCII_data:
            logger.info("HWID 显示已启用")
            return "PASSED"
        else:
            logger.info("启用 HWID 失败")
            return "FAILED"

    def Disable_HWID(self):
        """禁用 HWID 显示（某些机型默认显示）"""
        if self.dut is None:
            logger.info("DUT 未连接，无法禁用 HWID")
            return "FAILED"
        hexdata, ASCII_data = self.dut.send_hex_cmd(
            "055A2600920F41542B454750494F3D4750494F5F5345545F414C4C3A33392C302C312C302C322C300D0A",
            delay=0.05,
        )
        logger.info(f"Disable_HWID raw response: {ASCII_data}")
        if "di=0" in ASCII_data:
            logger.info("HWID 显示已禁用")
            return "PASSED"
        else:
            logger.info("禁用 HWID 失败")
            return "FAILED"

    # ═══════════════════════════════════════════════════════════════════════
    #  Fixture 初始化 / 收尾
    # ════════════════════════════════════
    def Fixture_init(self):
        """Fixture 初始化：关闭所有电源输出 + DMM 清错 + 断开全部继电器"""
        try:
            if self._ps_ok:
                self._ps.output_off_all()
            if self._dmm_ok:
                self._dmm.set_DMMcls()
            if self._relay_ok:
                self._relay.turn_off_relays(range(1, 9))
            return "PASSED"
        except Exception as e:
            logger.info(f"Fixture_init 异常: {e}")
            return "FAILED"

    def Finished(self):
        """测试完成收尾：关闭所有电源 + DMM 清错 + 断开全部继电器"""
        try:
            if self._ps_ok:
                self._ps.output_off_all()
            if self._dmm_ok:
                self._dmm.set_DMMcls()
            if self._relay_ok:
                self._relay.turn_off_relays(range(1, 9))
            return True
        except Exception as e:
            logger.info(f"Finished 异常: {e}")
            return False
