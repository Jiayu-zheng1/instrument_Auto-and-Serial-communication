"""DUT 身份信息 — 集中管理 FGSN、ScanSN 等散落属性。"""

from dataclasses import dataclass, field


@dataclass
class DUTInfo:
    """DUT 身份信息容器。"""
    scan_sn: str = ""
    fgsn: str = ""
    hwid: str = ""
    fw_version: str = ""
    mcu_fw_ver: str = ""
    soc_version: str = ""
    bt_fw_ver: str = ""
    aquila_id: str = ""
    otp_version: str = ""
    bundle_version: str = ""
    ntc_temperature: str = ""
    color_id: str = ""
    extra: dict = field(default_factory=dict)
