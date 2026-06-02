"""DUT serial communication module."""

import time
import serial
from serial.tools import list_ports
from app.utils.logger import get_logger

logger = get_logger("DUT")


def get_ports():
    ports = list(
        list_ports.grep(r"/dev/cu\.(usbmodem\w+|pencil\w*|Pencil\w*|Configuration\w*)")
    )
    if ports:
        logger.info(f"get_ports:{ports[0].device}")
    return ports


def find_port_by_location(location_id: str):
    """按 location ID 查找 DUT 串口。同时兼容两种 location 格式：
    - pyserial: '20-6.3.2'（直接从 comports 来）
    - system_profiler: '0x14633000'（去掉 0x 前缀匹配）

    location_id 为空时直接用 get_ports() 兜底。
    """
    if location_id:
        # 去掉 0x 前缀方便匹配
        loc_id = location_id.lower().replace("0x", "")
        for p in list_ports.comports():
            d = p.device or ""
            if "cu." not in d or "BLTH" in d or "Bluetooth" in d:
                continue
            # pyserial location
            p_loc = (getattr(p, "location", "") or "").lower()
            # system_profiler location: 从 device 名提取
            # 如 cu.usbmodem1463201 → 14632 可匹配 0x14633000
            import re
            m = re.search(r"usbmodem(\d+)", d)
            dev_loc = m.group(1) if m else ""

            if loc_id in p_loc or loc_id in dev_loc or p_loc in loc_id:
                logger.info(f"DUT location 匹配: {d} (pyserial_loc={p_loc})")
                return d
        # location_id 没匹配到，不继续兜底——可能 DUT 没插
        return None
    # 未设 location_id，用 get_ports 兜底
    ports = get_ports()
    return ports[0].device if ports else None


class Device:
    """Serial device under test."""

    def __init__(self):
        self.ser: serial.Serial = None

    def open_get_port(self, port, baudrate=921600):
        self.ser = serial.Serial(port=port, baudrate=baudrate, timeout=0.1)
        time.sleep(0.01)
        self.ser.write("\n".encode())

    def read_cmd(self):
        buffr = b""
        while True:
            data = self.ser.read_all()
            if data:
                buffr += data
            if data.endswith(b"[3G"):
                logger.info(f"read_data:{buffr.decode()}")
                break
        return buffr.decode()

    def clear_data(self):
        while True:
            data = self.ser.read_all()
            logger.debug(f"clear {data}")
            if not data:
                break

    def send_cmd(self, cmd):
        self.clear_data()
        self.ser.write((cmd + "\n").encode())
        logger.debug(f"send_cmd:{cmd}")

    def close_port(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def read_Write(self, cmd):
        self.send_cmd(cmd)
        time.sleep(0.01)
        return self.read_cmd()

    def send_hex_cmd(self, hex_str: str, delay: float = 0.05) -> tuple[str, str]:
        """发送 Hex 指令，返回 (原始hex值, ASCII解码结果)。"""
        self.ser.reset_input_buffer()
        raw = hex_str.strip().replace(" ", "")
        data = bytes.fromhex(raw)
        self.ser.write(data)
        time.sleep(delay)
        rx = self.ser.read_all()
        logger.info(f"send_hex_cmd sent: {hex_str}, received raw: {rx.hex()}")
        if not rx:
            return "", ""
        # 原始 hex 值
        raw_hex = rx.hex()
        # ASCII 解码结果
        ascii_str = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in rx)
        return raw_hex, ascii_str
