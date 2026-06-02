# Read Data — 制造测试自动化工具

DUT 串口通信 + 仪器控制 + 自动测试 + CSV 报表。支持手动/自动双模式，Location ID 监控 DUT 插拔即测。

## 技术栈

| 层 | 技术 |
|---|------|
| UI | PyQt5 + qfluentwidgets（Fluent Design 控件） |
| 串口 | pyserial（DUT）+ ioreg（macOS 监控串口插拔） |
| 仪器 | pyvisa + pyvisa-py（34970A DMM、IT6382 电源、Relayboard） |
| 日志 | loguru（按模块分文件 + 控制台 + UI 面板） |
| SFC | urllib（HTTP 方式上报 PASS/FAIL） |
| 配置 | JSON（系统配置 + 仪器配置 + Limits.csv） |

## 特性

- **双测试模式** — 手动输入 SN 点 Start / 自动模式监控串口即插即测
- **Location ID 监控** — ioreg 按 USB location 精准检测 DUT 插拔
- **Hex 指令协议** — `055A...0D0A` 格式发送，支持纯 hex 和 hex+regex 两种模式
- **仪器控制** — KEYSIGHT 34970A DMM（USB/GPIB）、IT6382 程控电源、8 路继电器板
- **SFC 上报** — 在线模式下自动向 SFC 系统上报测试结果
- **Fail 即停** — 通用设置可开关，失败后跳过后续测试项
- **模块化日志** — DUT / TestRunner / InstrumentManager / SFC 各自独立 `.log` 文件
- **macOS 风格设置页** — 左侧标签栏 + 右侧滚动卡片，滚动联动高亮，密码解锁
- **动画效果** — 状态卡片脉冲、DUT 连接呼吸灯

## 项目结构

```
Read_data/
├── main.py
├── requirements.txt
├── resources/
│   ├── Limits.csv                 # 测试项配置
│   ├── Error_Code.csv             # 错误码映射
│   └── logo_foxlink_b.png
├── app/
│   ├── application.py             # QApplication 启动
│   ├── controllers/
│   │   ├── test_runner.py          # QThread 测试执行引擎
│   │   ├── instrument_manager.py   # 仪器管理器单例
│   │   ├── dut_monitor.py          # DUT 串口监控线程 (ioreg + location ID)
│   │   └── log_controller.py       # loguru → Qt 信号桥接
│   ├── models/
│   │   ├── device.py               # DUT 串口通信 (send_hex_cmd / read_Write)
│   │   ├── test_item.py            # 测试业务逻辑 (DUT 命令 + 仪器读数)
│   │   ├── test_config.py          # CSV 行解析 + Pass/Fail 判定
│   │   ├── sfc_connector.py        # SFC HTTP 上报 (connect / checkRoute / upload)
│   │   └── instruments/
│   │       ├── keysight_34970a.py  # 34970A DMM
│   │       ├── ps_it6382.py        # IT6382 电源
│   │       └── relay_board.py      # 继电器板
│   ├── views/
│   │   ├── main_window.py          # 主窗口（菜单栏 + 信号连接）
│   │   ├── control_bar.py          # 顶栏（Logo / 仪器状态 / DUT 灯 / SN / Start / 计时器）
│   │   ├── status_header.py        # 状态卡片（Input / Fail / Yield / 测试结果）
│   │   ├── test_table.py           # 测试结果表格
│   │   ├── log_panel.py            # 实时日志面板
│   │   ├── settings_dialog.py      # macOS 风格设置（5 标签页）
│   │   ├── animations.py           # 脉冲 / 淡入淡出动画
│   │   └── theme.py                # HIG 主题（色彩 / 字体 / QSS）
│   └── utils/
│       ├── config.py               # 系统配置统一读写
│       ├── constants.py            # 全局常量
│       ├── limits_loader.py        # Limits.csv 统一加载解析
│       ├── logger.py               # 模块化日志（按模块分文件 + 轮转归档）
│       └── csv_handler.py          # 测试结果 CSV 生成
```

## 快速开始

### 环境

- macOS
- Python 3.12+
- NI-VISA 或 pyvisa-py

```bash
pip install -r requirements.txt
python main.py
```

### 手动模式

1. 仪器连好后输入 SN
2. 点 **Start** 或回车开始测试

### 自动模式

1. 设置页 → 串口设置 → 填入 DUT Location ID（用 `system_profiler SPUSBDataType` 查看）
2. 打开 **自动测试模式**
3. DUT 插入 → 自动开始测试 → 拔出 → 再插入 → 再次测试

## Limits.csv 配置

| 列 | 说明 |
|----|------|
| `TestItem` | 测试项显示名 |
| `TestName` | TestItem 方法名（`run_read_cmd` 或具体方法名） |
| `LowerLimit` / `UpperLimit` | 判定范围（数值 或 `PASSED`/`No Empty`） |
| `Running` | `Y` 加入测试序列 |
| `config` | 配置字典：`hex_cmd`、`regex`、`group`、`delay`、`contains` 等 |

config 格式示例：

```python
# 纯 hex — 发指令收返回即可
('hex_cmd':'055A02000c800D0A')

# hex + regex — 正则提取匹配值
('hex_cmd':'055A1200920F...','regex':'hw_id\\s\\W\\s(\\w+)','group':'1','delay':'1')
```

## 依赖

| 包 | 用途 |
|----|------|
| PyQt5 | UI 框架 |
| qfluentwidgets | Fluent Design 控件 |
| pyvisa + pyvisa-py | VISA 仪器通信 |
| pyserial | 串口通信 |
| loguru | 日志 |
