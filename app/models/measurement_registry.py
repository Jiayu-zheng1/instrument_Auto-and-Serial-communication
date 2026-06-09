"""测量方法注册表 — 信号名 → (测量类型, 通道号) 映射。

用法:
    from app.models.measurement_registry import MEASUREMENT_MAP
    method_type, channel = MEASUREMENT_MAP["Measure_Impedance_PP_VBUS_USBC_To_GND"]
    # → ("resistance", "101")
"""

# ═══════════════════════════════════════════════════════════════════════════
#  Slot 1 阻抗 (101–120)  —  20 个信号
# ═══════════════════════════════════════════════════════════════════════════

SLOT1_IMPEDANCE = {
    "Measure_Impedance_PP_VBUS_USBC_To_GND":       "101",
    "Measure_Impedance_PP_VBUS_RVP_To_GND":        "102",
    "Measure_Impedance_PP_VBUS_OUT_To_GND":        "103",
    "Measure_Impedance_PP_VBUS_CONN_To_GND":       "104",
    "Measure_Impedance_PP_VBATP_CON_To_GND":       "105",
    "Measure_Impedance_PP1V2_BUCK_OUT_To_GND":     "106",
    "Measure_Impedance_PP_PMID_CHG_To_GND":        "107",
    "Measure_Impedance_PP_VSYS_CHG_To_GND":        "108",
    "Measure_Impedance_PP_CHG_REGN_LDO_To_GND":    "109",
    "Measure_Impedance_PP_VBUS_HB_To_GND":         "110",
    "Measure_Impedance_PP1V8_SUR_TON_RIGHT_To_GND":"111",
    "Measure_Impedance_PP1V8_SUR_TON_LEFT_To_GND": "112",
    "Measure_Impedance_PP_LP5811_BOOST_To_GND":    "113",
    "Measure_Impedance_PP_VCHG_IN_To_GND":         "114",
    "Measure_Impedance_PP_VBAT_To_GND":            "115",
    "Measure_Impedance_PP_VSYS_To_GND":            "116",
    "Measure_Impedance_PP_VAUD_To_GND":            "117",
    "Measure_Impedance_PP1V8_VIO_To_GND":          "118",
    "Measure_Impedance_PP1V8_VDIG18_To_GND":       "119",
    "Measure_Impedance_PP3V1_VDD31_To_GND":        "120",
}

# ═══════════════════════════════════════════════════════════════════════════
#  Slot 2 阻抗 (201–217)  —  17 个信号
# ═══════════════════════════════════════════════════════════════════════════

SLOT2_IMPEDANCE = {
    "Measure_Impedance_PP1V8_VA18_To_GND":         "201",
    "Measure_Impedance_PP_VPA_To_GND":             "202",
    "Measure_Impedance_PP_DVDD_MLDO_To_GND":       "203",
    "Measure_Impedance_FSOURCE_D_To_GND":          "204",
    "Measure_Impedance_PP_VOX_CLK_To_GND":         "205",
    "Measure_Impedance_PP_VOX_DAT_To_GND":         "206",
    "Measure_Impedance_PDM_CLK_FF1_FB_To_GND":     "207",
    "Measure_Impedance_PDM_DAT_FF1_FB_To_GND":     "208",
    "Measure_Impedance_PDM_CLK_FF2_FF3_To_GND":    "209",
    "Measure_Impedance_PDM_DAT_FF2_FF3_To_GND":    "210",
    "Measure_Impedance_PP_VDD_To_GND":             "211",
    "Measure_Impedance_CC1_To_GND":                "212",
    "Measure_Impedance_CC2_To_GND":                "213",
    "Measure_Impedance_PP_VCORE_To_GND":           "214",
    "Measure_Impedance_PP_VRF_IN_To_GND":          "215",
    "Measure_Impedance_PP_VRTC_To_GND":            "216",
    "Measure_Impedance_PP_VSRAM_To_GND":           "217",
}

# ═══════════════════════════════════════════════════════════════════════════
#  Slot 1 电压 (101–120)  —  20 个信号
# ═══════════════════════════════════════════════════════════════════════════

SLOT1_VOLTAGE = {
    "Measure_Voltage_PP_VBUS_USBC_To_GND":         "101",
    "Measure_Voltage_PP_VBUS_RVP_To_GND":          "102",
    "Measure_Voltage_PP_VBUS_OUT_To_GND":          "103",
    "Measure_Voltage_PP_VBUS_CONN_To_GND":         "104",
    "Measure_Voltage_PP_VBAT_CON_To_GND":          "105",
    "Measure_Voltage_PP1V2_BUCK_OUT_To_GND":       "106",
    "Measure_Voltage_PP_PMID_CHG_To_GND":          "107",
    "Measure_Voltage_PP_VSYS_CHG_To_GND":          "108",
    "Measure_Voltage_PP_CHG_REGN_LDO_To_GND":      "109",
    "Measure_Voltage_PP_VBUS_HB_To_GND":           "110",
    "Measure_Voltage_PP1V8_SUR_TON_RIGHT_To_GND":  "111",
    "Measure_Voltage_PP1V8_SUR_TON_LEFT_To_GND":   "112",
    "Measure_Voltage_PP_LP5811_BOOST_To_GND":      "113",
    "Measure_Voltage_PP_VCHG_IN_To_GND":           "114",
    "Measure_Voltage_PP_VBAT_To_GND":              "115",
    "Measure_Voltage_PP_VSYS_To_GND":              "116",
    "Measure_Voltage_PP_VAUD_To_GND":              "117",
    "Measure_Voltage_PP1V8_VIO_To_GND":            "118",
    "Measure_Voltage_PP1V8_VDIG18_To_GND":         "119",
    "Measure_Voltage_PP3V1_VDD31_To_GND":          "120",
}

# ═══════════════════════════════════════════════════════════════════════════
#  Slot 2 电压 (201–217)  —  17 个信号
# ═══════════════════════════════════════════════════════════════════════════

SLOT2_VOLTAGE = {
    "Measure_Voltage_PP1V8_VA18_To_GND":           "201",
    "Measure_Voltage_PP_VPA_To_GND":               "202",
    "Measure_Voltage_PP_DVDD_MLDO_To_GND":         "203",
    "Measure_Voltage_FSOURCE_D_To_GND":            "204",
    "Measure_Voltage_PP_VOX_CLK_To_GND":           "205",
    "Measure_Voltage_PP_VOX_DAT_To_GND":           "206",
    "Measure_Voltage_PDM_CLK_FF1_FB_To_GND":       "207",
    "Measure_Voltage_PDM_DAT_FF1_FB_To_GND":       "208",
    "Measure_Voltage_PDM_CLK_FF2_FF3_To_GND":      "209",
    "Measure_Voltage_PDM_DAT_FF2_FF3_To_GND":      "210",
    "Measure_Voltage_PP_VDD_To_GND":               "211",
    "Measure_Voltage_CC1_To_GND":                  "212",
    "Measure_Voltage_CC2_To_GND":                  "213",
    "Measure_Voltage_PP_VCORE_To_GND":             "214",
    "Measure_Voltage_PP_VRF_IN_To_GND":            "215",
    "Measure_Voltage_PP_VRTC_To_GND":              "216",
    "Measure_Voltage_PP_VSRAM_To_GND":             "217",
}

# ═══════════════════════════════════════════════════════════════════════════
#  单点测量（不走批量扫描，直接读 DMM）
# ═══════════════════════════════════════════════════════════════════════════

DIRECT_MEASUREMENTS = {
    "Measure_Voltage_PP1V8_SUR_RST_LEFT_To_GND":  ("voltage", "112"),
}

# ═══════════════════════════════════════════════════════════════════════════
#  汇总：信号名 → (测量类型, 通道号)
# ═══════════════════════════════════════════════════════════════════════════

MEASUREMENT_MAP: dict[str, tuple[str, str]] = {}

for ch, name in {v: k for k, v in SLOT1_IMPEDANCE.items()}.items():
    MEASUREMENT_MAP[name] = ("resistance", ch)

for ch, name in {v: k for k, v in SLOT2_IMPEDANCE.items()}.items():
    MEASUREMENT_MAP[name] = ("resistance", ch)

for ch, name in {v: k for k, v in SLOT1_VOLTAGE.items()}.items():
    MEASUREMENT_MAP[name] = ("voltage", ch)

for ch, name in {v: k for k, v in SLOT2_VOLTAGE.items()}.items():
    MEASUREMENT_MAP[name] = ("voltage", ch)

for name, (mtype, ch) in DIRECT_MEASUREMENTS.items():
    MEASUREMENT_MAP[name] = (mtype, ch)
