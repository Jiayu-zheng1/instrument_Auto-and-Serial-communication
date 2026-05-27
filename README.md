# Instrument Auto & Serial Communication

Manufacturing test automation tool. Connects to DUT (Device Under Test) via serial, controls test instruments (DMM, power supply, relay board), runs automated test sequences, and exports CSV reports.

## Features

- **Serial Communication** — Auto-detect DUT serial port, send commands, parse responses with regex extraction
- **Instrument Control** — KEYSIGHT 34970A DMM (USB/GPIB), IT6382 programmable power supply, 8-channel relay board
- **Automated Test Sequence** — CSV-driven test configuration (`Limits.csv`) with configurable commands, regex parsing, and pass/fail evaluation
- **Real-time UI** — PyQt5 macOS-native interface with live test results table, log panel, status cards (Input / Fail / Yield), and elapsed timer
- **CSV Report Export** — Automatic test result CSV generation for PDCA upload
- **Dark Mode** — macOS system appearance auto-detection

## Architecture

```
app/
├── controllers/
│   ├── instrument_manager.py   # Singleton instrument lifecycle (connect/disconnect/reconnect)
│   ├── log_controller.py       # loguru → Qt signal bridge
│   └── test_runner.py          # QThread-based sequential test execution
├── models/
│   ├── device.py               # DUT serial communication
│   ├── test_config.py          # CSV row parsing & limit evaluation
│   ├── test_item.py            # Test procedures (DUT commands, DMM measurements, relay/PS control)
│   └── instruments/
│       ├── keysight_34970a.py  # 34970A DMM driver (USB/GPIB via pyvisa)
│       ├── ps_it6382.py        # IT6382 power supply driver
│       └── relay_board.py      # 8-channel relay board driver
├── utils/
│   ├── constants.py            # App-wide paths and config
│   └── csv_handler.py          # Test result CSV generation
└── views/
    ├── main_window.py          # Main window with native macOS menu bar
    ├── control_bar.py          # SN input, Start button, timer
    ├── status_header.py        # Metric cards (Input/Fail/Yield/Status)
    ├── test_table.py           # Test results table
    ├── log_panel.py            # Real-time log viewer
    ├── instrument_settings.py  # Instrument configuration dialog
    └── theme.py                # macOS HIG-compliant theme (light/dark)
```

## Quick Start

### Requirements

- macOS (Dark Mode supported)
- Python 3.12+
- NI-VISA or pyvisa-py backend

### Install

```bash
pip install -r requirements.txt
```

### Run

```bash
python main.py
```

### Test Configuration

Test items are defined in `resources/Limits.csv`:

| Column | Description |
|--------|-------------|
| `TestItem` | Test method name or display label |
| `LowerLimit` / `UpperLimit` | Pass/fail range (numeric or special: `No Empty`, `PASSED`) |
| `Running` | `Y` to include in test sequence |
| `config` | JSON/dict with `cmd`, `regex`, `group`, `action`, etc. |

## Dependencies

| Package | Purpose |
|---------|---------|
| PyQt5 | UI framework |
| pyvisa + pyvisa-py | VISA instrument communication |
| pyserial | Serial port communication |
| loguru | Logging |
| qfluentwidgets | Fluent Design instrument settings dialog |

## License

See [LICENSE](LICENSE).
