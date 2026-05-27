# Read Data — 制造测试自动化工具

制造测试自动化平台。通过串口连接 DUT（待测设备），控制测试仪器（数字万用表、程控电源、继电器板），执行自动化测试序列，并导出 CSV 测试报告供 PDCA 系统上传。

## 功能特性

- **串口通信** — 自动检测 DUT 串口（`/dev/cu.usbmodem*`、`/dev/cu.pencil*`），发送指令并解析响应（正则提取）
- **仪器控制** — KEYSIGHT 34970A 数字万用表（USB/GPIB 双模）、IT6382 三通道程控电源、8 路继电器板
- **自动化测试序列** — CSV 驱动测试配置（`resources/Limits.csv`），支持自定义指令、正则解析、数值范围判定、特殊规则（No Empty / PASSED / contains）
- **实时 UI** — PyQt5 macOS 原生界面：实时测试结果表格、日志面板、状态卡片（Input / Fail / Yield）、计时器、SN 扫码输入
- **CSV 报告导出** — 自动生成 PDCA 格式的测试结果 CSV（含上下限、测试项元数据）
- **深色模式** — 自动跟随 macOS 系统外观（Light / Dark）
- **仪器配置持久化** — 仪器端口、地址等配置保存至 JSON 文件，支持图形化设置对话框
- **PyInstaller 打包** — 支持打包为 macOS `.app` Bundle

## 架构设计

项目采用类 MVC 分层架构：

```
app/
├── controllers/                  # 控制层
│   ├── instrument_manager.py     # 仪器管理器（单例），后台线程自动检测连接/重连
│   ├── log_controller.py         # loguru → Qt 信号桥接，日志文件管理
│   └── test_runner.py            # QThread 测试执行引擎，顺序执行测试项
├── models/                       # 业务模型层
│   ├── device.py                 # DUT 串口通信（自动发现、读写、解析）
│   ├── test_config.py            # CSV 行解析、上下限判定（数值/特殊规则）
│   ├── test_item.py              # 测试过程：DUT 指令、DMM 测量、继电器/电源控制
│   └── instruments/              # 仪器驱动
│       ├── keysight_34970a.py    # 34970A DMM 驱动（USB/GPIB via pyvisa）
│       ├── ps_it6382.py          # IT6382 程控电源驱动
│       └── relay_board.py        # 8 路继电器板驱动（v0/v1 双版本协议）
├── utils/                        # 工具层
│   ├── constants.py              # 全局常量（路径、默认参数、版本号）
│   └── csv_handler.py            # PDCA 格式测试报告 CSV 生成
└── views/                        # 视图层（PyQt5）
    ├── main_window.py            # 主窗口 + 原生 macOS 菜单栏
    ├── control_bar.py            # SN 输入框、开始按钮、计时器
    ├── status_header.py          # 指标卡片（Input / Fail / Yield / Status）
    ├── test_table.py             # 测试结果表格
    ├── log_panel.py              # 实时日志查看器
    ├── instrument_settings.py    # 仪器配置对话框
    └── theme.py                  # macOS HIG 主题（Light / Dark 自动切换）
```

### 数据流

```
Limits.csv → TestConfig[] → TestRunner(QThread) → TestItem
                                                    ├── Device (串口 ↔ DUT)
                                                    ├── KEYSIGHT_34970A (DMM 测量)
                                                    ├── IT6382 (电源输出)
                                                    └── RELAYBOARD (通道切换)
                                                          │
                                                    Qt Signals → UI 更新
                                                    CsvReport → CSV 文件
```

## 环境要求

| 依赖 | 版本要求 |
|------|---------|
| macOS | 10.15+（支持 Dark Mode） |
| Python | 3.12+ |
| NI-VISA 或 pyvisa-py | 仪器通信后端 |
| FTDI USB 串口驱动 | 继电器板 / DMM USB 连接 |

## 快速开始

### 安装

```bash
pip install -r requirements.txt
```

### 运行

```bash
python main.py
```

### 打包为 macOS App

```bash
pyinstaller build.spec
```

打包产物位于 `dist/Read_Data.app`。

## 依赖项

| 包 | 用途 |
|---|------|
| PyQt5 | UI 框架 |
| pyvisa + pyvisa-py | VISA 仪器通信（支持 NI-VISA / pyvisa-py 双后端） |
| pyserial | 串口通信（DUT + 继电器板） |
| loguru | 日志系统 |
| qfluentwidgets | Fluent Design 风格仪器设置对话框 |

## 测试配置（Limits.csv）

测试项定义在 `resources/Limits.csv`，字段说明：

| 字段 | 说明 |
|------|------|
| `TestItem` | 测试方法名（对应 `TestItem` 类中的方法）或显示标签 |
| `LowerLimit` | 下限值（数值、`No Empty`、`PASSED`、`ON`、`True`） |
| `UpperLimit` | 上限值（数值、`No Empty`、`PASSED`、`ON`、`True`） |
| `Running` | `Y` = 加入测试序列，`N` = 跳过 |
| `config` | JSON/dict 配置，支持以下 key： |

### config 支持的配置项

| Key | 说明 |
|-----|------|
| `action` | `"method"` 直接调用同名方法 / `"connect"` 连接 DUT |
| `cmd` / `command` / `instruction` | 发送到 DUT 的串口指令 |
| `pre_cmds` / `post_cmds` | 前置/后置指令列表 |
| `regex` | 正则表达式（从 DUT 回传中提取值） |
| `group` / `position` | 正则捕获组编号（默认 1） |
| `groups` | 多捕获组（如 `[1,2,3]`） |
| `match_index` / `index` | 匹配索引（默认 0 = 第一个匹配） |
| `contains` | 包含检查（匹配则返回 `pass_value`） |
| `pass_value` / `fail_value` | contains 模式下的返回值 |
| `strip` | 是否去除首尾空白（默认 true） |
| `cast` | 类型转换 — `"str"` / `"int"` / `"float"` / `"hex_int"` |
| `delay` | 指令后延时（秒） |
| `set_attr` | 将结果赋值到 TestItem 属性 |
| `default` | 正则无匹配时的默认值 |

### 配置示例

```csv
TestItem,LowerLimit,UpperLimit,value,Result,Running,config
MCU_FW_Ver,No Empty,No Empty,,,Y,"{'cmd':'sys version','regex':'Application\\s\\W\\d\\d\\W\\S\\s(\\w*)','group':1}"
Measure_Impedance_PP_VBUS_To_GND,1000,5000,,,Y,
FinishSetting,PASSED,PASSED,,,Y,"{'cmd':'stylus uvp','contains':'UVP mode','pass_value':'PASSED','fail_value':'FAILED'}"
```

### 判定规则

- **数值范围**：`LowerLimit ≤ value ≤ UpperLimit` → Pass，否则 Fail
- **No Empty / Empty**：值非空 → Pass，空 → Fail
- **PASSED / ON / True**：自动判定为 Pass
- **contains**：回传数据包含指定字符串 → `pass_value`，否则 `fail_value`

## 仪器详情

### KEYSIGHT 34970A 数字万用表

- **连接方式**：USB（FTDI 串口适配器 via pyvisa-py）/ GPIB（NI-VISA）
- **支持测量**：二线电阻（Ω）、直流电压（V / mV）
- **扫描能力**：批量扫描（每批最多 10 通道），支持 Slot 1 (101–120) 和 Slot 2 (201–217)
- **配置**：`dmm_mode` (`usb`/`gpib`)、`dmm_port`、`dmm_gpib`

### IT6382 程控电源

- **连接方式**：USB / GPIB
- **通道数**：3 通道独立输出
- **支持操作**：单通道/三通道同时输出/关闭、电压/电流读取（mV / mA）

### 8 路继电器板

- **连接方式**：USB 串口
- **版本**：v0 (19200bps) / v1 (9600bps)，不同命令协议
- **支持操作**：单通道/范围/全部开关、断电自动重连

## VISA 诊断工具

运行 `visa_demo.py` 可扫描所有可用 VISA 资源并尝试连接查询 `*IDN?`：

```bash
python visa_demo.py
```

该工具支持 NI-VISA 和 pyvisa-py 双后端检测，用于排查仪器连接问题。

## 日志与报告

| 目录 | 内容 |
|------|------|
| `~/Documents/SpartaLog/TopLevelLog/` | 测试日志文件（90 天自动清理） |
| `~/Documents/SpartaLog/Test_CSV/` | PDCA 格式测试报告 CSV |
| `~/Documents/SpartaLog/instrument_config.json` | 仪器配置持久化 |

## 版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.0.1 | 2026-05 | 当前版本：34970A 扫描测量、MVC 重构、仪器配置 UI、macOS 深色模式 |

## 开发

- **作者**：Peng Wu, Foxlink TE
- **站点**：FLDG
- **产品**：—

## 许可

详见 [LICENSE](LICENSE)。
