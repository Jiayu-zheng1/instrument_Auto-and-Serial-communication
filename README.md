# Read Data — 制造测试自动化工具

Foxlink TE 部门的桌面制造测试工具。通过串口与 DUT 通信，控制仪器（34970A DMM / IT6382 电源 / Relayboard 继电器板），执行自动化测试序列，生成 CSV 报表，并上报 SFC 系统。支持单通道和多通道并行测试。

## 技术栈

| 层 | 技术 |
|---|------|
| UI | PyQt5 + qfluentwidgets（Fluent Design 控件） |
| 串口 | pyserial（DUT + 继电器板） |
| 仪器通信 | pyvisa + pyvisa-py（GPIB 用 NI-VISA，USB 串口用 pyvisa-py） |
| 日志 | loguru — 按模块分文件，每天午夜轮转，历史归档到日期文件夹 |
| SFC | urllib3（HTTP 方式上报 PASS/FAIL） |
| 配置 | JSON（system_config.json + instrument_config.json）+ CSV（Limits.csv） |

## 快速开始

### 环境要求

- macOS 10.15+
- Python 3.12+
- NI-VISA（GPIB 仪器需要，USB 模式可选）
- FTDI USB 转串口驱动（34970A USB 连接需要）

### 安装与启动

```bash
pip install -r requirements.txt
python main.py
```

### 首次使用

1. 连好仪器后**重启软件**，等待仪器自动检测完成
2. 顶栏圆点变绿表示仪器就绪：●34970A ●IT6382 ●Relay ●DUT
3. 输入 SN → 点 **Start** 或按回车开始测试

## 特性

- **双测试模式** — 手动输入 SN 点 Start / 自动模式监控 DUT 串口插拔即测
- **多通道并行测试** — 最多 8 个通道同时测试独立 DUT，每通道独立串口 + 独立 Start
- **多 DMM 支持** — 支持多台 34970A，一对一绑定通道
- **Summary 汇总页** — 多通道模式下 Tab 切换，网格卡片显示各通道 PASS/FAIL/Yield
- **Location ID 精准匹配** — ioreg IOTTYSuffix 4 级匹配识别 USB 设备，解决同 hub 下串口号混淆
- **Hex 指令协议** — `055A...0D0A` 格式，支持纯 hex 和 hex+regex 值提取
- **Config 驱动测试** — 测试逻辑完全由 Limits.csv 的 config 列定义，无需改代码
- **Config 新旧兼容** — 同时支持 `('key':'val')` 旧格式和 `hex_cmd 055A...` Atlas2 风格空格分隔新格式
- **仪器控制** — 34970A（USB/GPIB，电阻/电压扫描+单点测量）、IT6382（3 路电源输出）、8 路继电器板（v0/v1 两版硬件）
- **Fail 即停** — 失败后跳过后续项（可开关）
- **SFC 上报** — 在线模式下 connect → checkRoute → uploadResult（OK/NG）
- **面向对象架构** — BaseInstrument 仪器抽象基类、BaseTestRunner 模板方法基类、MEASUREMENT_MAP 动态方法绑定
- **macOS 风格设置页** — 左侧标签栏 + 右侧滚动卡片，滚动联动高亮，密码 "123" 解锁
- **SN 通道后缀** — 多通道模式下 SN 自动加 `_CH1`、`_CH2` 后缀区分测试归属

## 项目结构

```
Read_data/
├── main.py                          # 入口
├── requirements.txt                 # Python 依赖
├── build.spec                       # PyInstaller 打包配置
├── resources/
│   ├── Limits.csv                   # 测试项配置（97 项）
│   ├── Error_Code.csv               # 错误码映射
│   ├── logo_foxlink_b.png           # Logo（深色）
│   ├── wlogo_foxlink_s.png          # Logo（浅色）
│   └── Foxlink.icns                 # macOS 应用图标
└── app/
    ├── application.py               # QApplication 启动
    ├── controllers/
    │   ├── base_runner.py            # 测试执行引擎基类（模板方法模式）
    │   ├── test_runner.py            # 单通道测试执行（SFC + CSV）
    │   ├── channel_runner.py         # 多通道测试执行（通道日志 + 串口定位）
    │   ├── instrument_manager.py     # 仪器管理器单例（多态 _check_instrument）
    │   ├── dut_monitor.py            # DUT 插拔监控（ioreg + location ID）
    │   └── log_controller.py         # loguru → Qt 信号桥接
    ├── models/
    │   ├── device.py                 # DUT 串口通信 + USB 定位
    │   ├── test_item.py              # 测试业务逻辑核心
    │   ├── test_config.py            # CSV 行解析 + Pass/Fail 判定
    │   ├── sfc_connector.py          # SFC HTTP 上报
    │   ├── measurement_registry.py   # 75 个测量信号 → (类型, 通道) 映射
    │   ├── dut_info.py               # DUT 身份信息容器 (dataclass)
    │   └── instruments/
    │       ├── base.py               # BaseInstrument ABC（统一 connect/disconnect/identity）
    │       ├── keysight_34970a.py    # 34970A DMM（USB 串口/GPIB，批量扫描）
    │       ├── ps_it6382.py          # IT6382 可编程电源（3 通道）
    │       └── relay_board.py        # 继电器板（v0/v1 两版）
    ├── views/
    │   ├── main_window.py            # 主窗口（菜单栏 + QStackedWidget）
    │   ├── control_bar.py            # 顶栏（仪器状态/SN/Start/计时器）
    │   ├── status_header.py          # 状态卡片（Input/Fail/Yield/状态）
    │   ├── test_table.py             # 测试结果表格
    │   ├── log_panel.py              # 实时日志面板
    │   ├── settings_dialog.py        # macOS 风格设置（5 标签页）
    │   ├── channel_tab.py            # 多通道单通道 Tab（SN+表格+日志）
    │   ├── summary_tab.py            # 多通道汇总 Tab（网格 PASS/FAIL）
    │   ├── animations.py             # 脉冲呼吸 / 淡入淡出
    │   └── theme.py                  # Apple HIG 主题（色彩/字体/QSS）
    └── utils/
        ├── config.py                 # 系统配置读写
        ├── config_parser.py          # Config 列解析（旧/新格式兼容）
        ├── constants.py              # 全局常量
        ├── limits_loader.py          # Limits.csv 加载解析
        ├── logger.py                 # 模块化日志（按天轮转+归档+过期清理）
        └── csv_handler.py            # 测试结果 CSV 生成
```

## 配置系统

### 数据目录

所有持久化数据存放在 `~/Documents/SpartaLog/`：

```
~/Documents/SpartaLog/
├── system_config.json               # 系统配置
├── instrument_config.json           # 仪器连接配置
├── TopLevelLog/                     # 日志
│   ├── InstrumentManager.log        # 今天活跃日志
│   ├── TestRunner.log
│   ├── ChannelRunner.log
│   ├── 2026-06-02/                  # 历史日志（每天一个文件夹）
│   │   ├── InstrumentManager.log
│   │   └── ...
│   └── 2026-06-01/
│       └── ...
└── Test_CSV/                        # 测试结果 CSV
```

### 系统配置键名说明

| 键 | 默认值 | 说明 |
|---|---|---|
| `log_retention_days` | 90 | 日志保留天数，过期自动删除 |
| `dut_baud_rate` | 921600 | DUT 串口波特率 |
| `dut_location_id` | `""` | DUT USB Location ID（单通道模式） |
| `auto_test_mode` | false | 自动测试模式，监控 DUT 插拔即测 |
| `fail_stop_test` | true | 测试项失败后停止后续测试 |
| `auto_scroll_log` | true | 日志面板自动滚动 |
| `sfc_url` | `""` | SFC 服务器 URL |
| `sfc_online` | false | 是否启用 SFC 在线上报 |
| `sfc_vip` | `""` | SFC 终端 IP 地址 |
| `multi_channel_mode` | false | 启用多通道测试模式 |
| `channel_count` | 4 | 通道数量（1–8） |
| `channel_location_ids` | `["","","",""]` | 每通道的 DUT Location ID |
| `channel_instruments` | `["","","",""]` | 每通道绑定的仪器（`"34970A"`/`"IT6382"`/`"Relayboard"`/`""`） |

### Limits.csv 配置

每行定义一个测试项：

| 列 | 说明 |
|---|---|
| `TestItem` | 测试项显示名称 |
| `TestName` | 对应 `TestItem` 中的方法名，或 `run_read_cmd` 走 config 驱动 |
| `LowerLimit` / `UpperLimit` | 判定范围（数值，或 `PASSED`/`No Empty` 等特殊值） |
| `Unit` | 单位（`mV` / `ohm` / `V` / `mA`） |
| `Running` | `Y` = 加入测试序列，`N` = 跳过 |
| `config` | 驱动参数（见下文） |

**config 格式示例：**

```python
# 纯 hex 指令 — 发送命令接收返回即可
('hex_cmd':'055A02000c800D0A')

# hex + regex 提取 — 正则匹配返回值
('hex_cmd':'055A1200920F...','regex':'hw_id\\s\\W\\s(\\w+)','group':'1','delay':'1')

# contains 检查 — 判断返回值是否包含指定字符串
('hex_cmd':'055A...', 'contains':'OK')

# 带延迟 + 前后置命令
('hex_cmd':'055A...', 'delay':'0.5', 'pre_cmds':'...', 'post_cmds':'...')
```

config 字段一览：
- `hex_cmd` — 要发送的 hex 指令字符串
- `cmd` / `command` / `instruction` — ASCII 命令
- `regex` — 正则表达式提取值
- `group` — 正则捕获组编号
- `delay` — 指令间延时（秒）
- `contains` — 检查返回值是否包含指定文本
- `pre_cmds` — 前置命令
- `post_cmds` — 后置命令
- `set_attr` — 执行后设置 TestItem 属性

## 使用说明

### 基本操作

1. **连接仪器** — 启动软件后仪器自动检测，顶栏圆点 ●34970A / ●IT6382 / ●Relay / ●DUT 变绿表示连接成功
2. **设置** — 点击 ⚙ 齿轮图标进入设置页，输入密码 `123` 解锁编辑
3. **单通道测试** — 关闭多通道模式，输入 SN → 点 **Start**
4. **多通道测试** — 设置页 → 串口设置 → 开启多通道测试模式 → 配置通道数量 + 每通道 Location ID + 绑定仪器 → 保存重启 → 各通道 Tab 独立操作

### 手动模式

1. 确保仪器已连接
2. 输入 SN
3. 点 **Start** 或按 Enter 开始测试
4. 结果实时显示在表格中，完成后生成 CSV 报表

### 自动模式

1. 设置页 → 串口设置 → 填入 DUT Location ID
2. 打开"自动测试模式"开关
3. 插入 DUT → 自动开始测试 → 拔出 → 再插入 → 再次测试

### 多通道测试

1. **配置**：设置页 → 串口设置 → 开启"多通道测试模式" → 选择通道数量 → 每个通道填入 Location ID + 选择绑定仪器 → 保存并重启
2. **查看 DUT**：点击"可用 DUT 设备"查看当前连接的 DUT 及 Location ID
3. **测试**：
   - 切换到各通道 Tab → 输入 SN → 点 **Start**（各通道独立启动）
   - 或点顶栏 **全局 Start** 同时启动所有通道
4. **查看汇总**：Summary Tab 显示各通道 PASS/FAIL 计数和 Yield

### 检查 DUT Location ID

```bash
system_profiler SPUSBDataType | grep -A 10 "FTDI\|USB-Serial\|CP210"
```

或点击设置页的"可用 DUT 设备"按钮查看。

## 仪器

### 34970A 数字万用表

- **USB 模式**：FTDI 适配器串口连接，波特率 9600
- **GPIB 模式**：NI-VISA 连接，需安装 NI-VISA 驱动
- **功能**：2 线电阻测量、直流电压测量、批量扫描（每批最多 10 通道）

### IT6382 程控电源

- **GPIB 模式**：NI-VISA 连接
- **USB 模式**：串口连接，支持自动检测
- **功能**：3 路独立输出、电压/电流读取

### Relayboard 继电器板

- 串口直连，支持 v0（19200 baud）和 v1（9600 baud + 校验）两版
- 8 路独立控制、批量控制、电源保护自动断电

## 打包

使用 PyInstaller：

```bash
pyinstaller build.spec
```

输出 `dist/Read_Data.app`。

## 维护

- **日志查看**：`~/Documents/SpartaLog/TopLevelLog/`，历史按日期归档
- **CSV 报表**：`~/Documents/SpartaLog/Test_CSV/`
- **修改测试项**：编辑 `resources/Limits.csv`
- **修改仪器端口**：设置页中修改或直接编辑 `~/Documents/SpartaLog/instrument_config.json`
- **重置配置**：删除 `~/Documents/SpartaLog/system_config.json`，重启即恢复默认
