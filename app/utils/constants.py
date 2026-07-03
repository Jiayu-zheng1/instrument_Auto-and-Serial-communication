"""Application-wide constants."""

import os

APP_NAME = "instrument_Auto-and-Serial-communication"
APP_VERSION = "1.0.1"
PRODUCT = ""
SITE = "FLDG"

RESOURCE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "resources")
MAIN_CSV = os.path.join(RESOURCE_DIR, "Main.csv")
LIMITS_CSV = os.path.join(RESOURCE_DIR, "Limits.csv")

LOG_DIR = os.path.expanduser("~/Documents/SpartaLog/TopLevelLog")
CSV_DIR = os.path.expanduser("~/Documents/SpartaLog/Test_CSV")
CONFIG_DIR = os.path.expanduser("~/Documents/SpartaLog")
INSTRUMENT_CONFIG_PATH = os.path.join(CONFIG_DIR, "instrument_config.json")
CHANNEL_CONFIG_PATH = os.path.join(CONFIG_DIR, "channel_config.json")

DEFAULT_BAUDRATE = 115200
SERIAL_TIMEOUT = 0.1
DUT_CONNECT_TIMEOUT = 5

SN_MAX_LENGTH = 10
