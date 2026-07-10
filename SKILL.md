---
name: network-device-automation
description: 网络设备运维自动化技能。此技能应在需要对网络设备（华为、H3C、思科、锐捷等）进行运维操作时使用，包括SSH/Telnet/串口连接、配置管理、故障诊断、健康巡检、批量操作等场景。支持交互式输入连接信息，适用于日常运维、批量管理、故障应急处理和自动化巡检任务。
---

# 网络设备运维自动化技能

本技能提供网络设备自动化运维能力，支持主流网络设备厂商的统一管理。

## 技能用途

本技能用于网络设备的自动化运维操作，包括但不限于：
- 设备连接管理（SSH/Telnet/串口）
- 命令执行（逐条执行，遇错中断）
- 配置查询、备份和恢复
- 设备健康检查和巡检
- 故障诊断和应急处理
- 批量设备操作

## 支持的设备厂商

- 华为 (Huawei)
- 华三 (H3C)
- 思科 (Cisco IOS/NX-OS)
- 锐捷 (Ruijie)
- 其他支持标准CLI的设备

## 核心架构

```
scripts/
├── 【核心层】基础组件
│   ├── base_executor.py       # 执行器基类（命令帮助查询）
│   ├── asset_manager.py       # 资产台账管理器
│   └── experience_manager.py  # 经验库管理器
│
├── 【执行层】厂商专属执行器
│   ├── h3c_executor.py        # H3C设备执行器
│   ├── huawei_executor.py     # 华为设备执行器
│   ├── cisco_executor.py      # 思科设备执行器
│   └── ruijie_executor.py     # 锐捷设备执行器
│
└── 【应用层】业务功能
    ├── config_backup.py       # 配置备份/恢复
    ├── health_check.py        # 健康检查/巡检
    └── batch_manager.py       # 批量操作
```

## 资产台账功能

本技能集成了资产台账功能，支持提前录入设备信息，使用时自动查找匹配，大幅节省token。

### 资产台账管理

使用资产管理器管理设备资产：

```bash
python scripts/asset_manager.py <命令> [参数...]
```

**可用命令:**

| 命令 | 说明 | 示例 |
|------|------|------|
| `list [分组] [标签]` | 列出所有设备 | `list core` |
| `find <IP\|名称>` | 查找设备 | `find 192.168.1.1` |
| `add` | 添加新设备（交互式） | `add` |
| `update <设备ID>` | 更新设备信息 | `update core-sw-01` |
| `delete <设备ID>` | 删除设备 | `delete core-sw-01` |
| `export [文件]` | 导出为JSON | `export backup.json` |
| `import <文件>` | 从JSON导入 | `import backup.json` |
| `groups` | 列出所有分组 | `groups` |

### 设备匹配规则

资产台账支持多字段智能匹配：
- **IP地址**: 完全匹配 `host` 字段
- **主机名**: 完全匹配 `host` 字段
- **设备名称**: 完全匹配 `name` 字段
- **设备ID**: 完全匹配台账中的设备键名
- **模糊匹配**: 部分匹配 `name` 或 `description` 字段

### 资产台账数据结构

资产台账文件位置: `assets/inventory.yaml`

```yaml
devices:
  core-sw-01:
    name: "核心交换机-01"
    host: "192.168.1.1"
    device_type: "hp_comware"
    vendor: "H3C"
    model: "S6850"
    username: "admin"
    password: ""  # base64编码，留空则交互式输入
    port: 22
    enable_password: ""
    group: "core"
    description: "核心交换机-机房A"
    location: "机房A-机柜01"
    contact: "张三"
    tags: ["core", "production"]
    created_at: "2025-01-17"
    updated_at: "2025-01-17"
```

## 厂商专属执行器

每个厂商都有专属的执行器，负责连接设备并执行命令。执行器自动集成经验库，处理已知问题。

### 统一接口格式

```bash
# 优先使用资产台账查找（推荐，节省token）
python scripts/<vendor>_executor.py --device <设备标识> --commands "<命令1>" "<命令2>"

# 降级使用显式连接参数
python scripts/<vendor>_executor.py --host <IP> --username <用户> --password <密码> --commands "<命令1>"
```

### H3C执行器

```bash
# 从资产台账查找
python scripts/h3c_executor.py --device 192.168.56.3 --commands "display version" "display vlan"

# 显式连接参数
python scripts/h3c_executor.py --host 192.168.56.3 --username admin --password xxx --commands "display version"

# 从JSON文件读取命令
echo '["display version", "display vlan"]' | python scripts/h3c_executor.py --device 192.168.56.3 --commands-json -

# 保存结果到文件
python scripts/h3c_executor.py --device 192.168.56.3 --commands "display version" --output result.json

# 查询命令帮助
python scripts/h3c_executor.py --host 10.0.254.2 --username admin --password xxx \
  --query-help "undo nat server protocol tcp global current-interface"

# 命令失败时自动查询帮助
python scripts/h3c_executor.py --host 10.0.254.2 --username admin --password xxx \
  --commands "display version" --auto-help
```

**H3C执行器特点：**
- 使用 `invoke_shell` 模式（更稳定）
- 自动处理分页（`---- More ----`）
- 自动修复 `save` 命令（添加 `force` 参数）
- 支持从资产台账查找设备
- **支持命令帮助查询**（`--query-help` 查询语法，`--auto-help` 失败时自动查询）

### 华为执行器

```bash
# 执行命令
python scripts/huawei_executor.py --device 192.168.1.1 --commands "display version" "display vlan"

# 查询命令帮助
python scripts/huawei_executor.py --host 192.168.1.1 --username admin --password xxx \
  --query-help "undo nat"

# 命令失败时自动查询帮助
python scripts/huawei_executor.py --device 192.168.1.1 --commands "display version" --auto-help
```

**华为执行器特点：**
- 使用 `invoke_shell` 模式
- 自动处理分页（`---- More ----`）
- 与H3C类似的CLI风格
- **支持命令帮助查询**（`--query-help` / `--auto-help`）

### 思科执行器

```bash
# 执行命令
python scripts/cisco_executor.py --device 192.168.1.1 --commands "show version" "show vlan brief"

# 查询命令帮助
python scripts/cisco_executor.py --host 192.168.1.1 --username admin --password xxx \
  --query-help "no ip nat"

# 命令失败时自动查询帮助
python scripts/cisco_executor.py --device 192.168.1.1 --commands "show version" --auto-help
```

**思科执行器特点：**
- 使用 `invoke_shell` 模式
- 自动处理分页（`--More--`）
- 支持 `enable` 密码
- 与华为/H3C不同的命令语法（`show` vs `display`）
- **支持命令帮助查询**（`--query-help` / `--auto-help`）

### 锐捷执行器

```bash
# 执行命令
python scripts/ruijie_executor.py --device 192.168.1.1 --commands "show version" "show vlan"

# 查询命令帮助
python scripts/ruijie_executor.py --host 192.168.1.1 --username admin --password xxx \
  --query-help "no ip nat"

# 命令失败时自动查询帮助
python scripts/ruijie_executor.py --device 192.168.1.1 --commands "show version" --auto-help
```

**锐捷执行器特点：**
- 使用 `invoke_shell` 模式
- 自动处理分页（`--More--` / `---- More ----`）
- 与思科类似的CLI风格
- **支持命令帮助查询**（`--query-help` / `--auto-help`）

### 串口执行器（console 口运维）

```bash
# 直接指定串口
python scripts/serial_executor.py --port COM3 --commands "display version" "display interface brief"

# 从资产台账查找串口设备
python scripts/serial_executor.py --device sw-console --commands "show running-config"

# 指定波特率 + 多厂商命令（华为/思科/H3C 通用）
python scripts/serial_executor.py --port COM3 --baud 9600 --commands "show ip route"

# 遇错中断（默认每条都执行）
python scripts/serial_executor.py --port COM3 --commands "show version" --stop-on-error
```

**串口执行器特点：**
- 基于 pyserial，通过 **console 串口**连接（SSH/Telnet 不可用、或新设备开局/配置恢复时使用）
- 自动处理分页：华为/H3C `---- More ----`、思科 `--More--`
- 自动确认 `[Y/N]`、支持多行命令（`\n` 自动转 `\r\n`）
- 与 SSH 执行器**统一接口**（`--device/--commands`，返回 JSON）
- 资产台账登记串口设备：`device_type: serial`、`port: COM3`、`baud_rate: 9600`
- 简易错误识别（含 `Error`/`Invalid`/`Unrecognized` 等标记 error 字段）

**资产台账串口设备示例：**
```yaml
devices:
  sw-console:
    name: "S220-console"
    device_type: serial
    port: COM3
    baud_rate: 9600
    vendor: huawei
    description: "S220 交换机 console 口"
```

### 执行器返回格式

所有执行器统一返回JSON格式：

```json
{
  "success": true,
  "executed": 2,
  "total": 3,
  "failed_at": null,
  "results": [
    {
      "command": "display version",
      "success": true,
      "output": "H3C Comware Software...",
      "error": null,
      "help": null
    },
    {
      "command": "display vlan",
      "success": false,
      "output": "% Error: Unrecognized command",
      "error": "命令执行错误: Unrecognized command",
      "help": "display vlan ?\r\n  vpn-instance  Specify a VPN instance\r\n..."
    }
  ]
}
```

**字段说明：**
- `command`: 执行的命令
- `success`: 是否成功
- `output`: 命令输出
- `error`: 错误信息（如有）
- `help`: 帮助信息（使用 `--auto-help` 时自动获取）

## 核心工作流程

### 1. 命令执行流程

```
用户需求
    │
    ▼
大模型生成命令列表
    │
    ▼
根据设备类型选择对应厂商执行器
    │
    ▼
执行器逐条执行命令
    │
    ├─ 成功 → 继续下一条
    │
    └─ 失败 → 中断，返回错误
            │
            ▼
         是否启用 auto-help？
            │
      ┌─────┴─────┐
      ▼           ▼
     是          否
      │           │
      ▼           ▼
  自动查询帮助   直接返回错误
      │           │
      └─────┬─────┘
            ▼
         大模型接收错误/帮助
            │
            ▼
      查询经验库处理方法
            │
      ┌─────┴─────┐
      ▼           ▼
   有经验       无经验
      │           │
      ▼           ▼
   应用方案    尝试解决
      │           │
      └─────┬─────┘
            ▼
      修改命令后重试
            │
            ▼
      如果是脚本问题
            │
            ▼
      修改执行器代码
```

### 2. 设备查找流程

执行器支持智能查找设备信息：

```
用户调用: --device 192.168.56.3
    │
    ▼
查询资产台账
    │
    ├─ 找到设备 ─────────────────────────────────┐
    │   │                                        │
    │   ▼                                        │
    │ 检查密码是否存储                            │
    │   │                                        │
    │   ├─ 已存储 ─────────────────────────────┐ │
    │   │                                       │ │
    │   └─ 未存储 → 交互式输入密码              │ │
    │                                           │ │
    └─ 未找到 → 提示用户选择:                    │ │
        1. 添加到台账                            │ │
        2. 使用显式参数(--host/--username)       │ │
                                                 │ │
        ┌────────────────────────────────────────┘ │
        │                                           │
        ▼                                           ▼
   使用台账信息连接                          使用显式参数连接
```

### 3. 配置管理

备份、恢复或对比设备配置：

```python
python scripts/config_backup.py
```

功能：
- **备份**: 将当前配置保存到本地文件（按日期和设备命名）
- **恢复**: 从备份文件恢复配置
- **对比**: 比较运行配置与启动配置或备份文件的差异

### 4. 健康检查与巡检

执行设备健康检查和自动巡检：

```python
python scripts/health_check.py
```

检查项目包括：
- CPU和内存使用率
- 接口状态和流量统计
- 路由表完整性
- ARP/MACTable状态
- 日志中的错误和告警
- 端口错误和丢包统计
- 冗余协议状态（VRRP/HSRP/Standalone）

巡检结果输出为结构化报告，支持JSON和Markdown格式。

### 5. 批量设备操作

对多台设备执行相同操作：

```python
python scripts/batch_manager.py
```

使用场景：
- 批量配置变更
- 批量巡检和健康检查
- 批量配置备份
- 批量命令执行

## 经验库系统

经验库记录实际遇到的问题和解决方案，执行器会自动应用相关经验。

### 经验库位置

```
experiences/
├── index.json              # 经验索引
├── 001_command_execution.json  # H3C使用exec_command超时
├── 002_pagination.json         # 分页处理
├── 003_encoding.json           # Windows编码问题
└── 004_script_error.json       # save命令force参数
```

### 经验库管理

```python
# 查看所有经验
python scripts/experience_manager.py

# 搜索经验
python scripts/experience_manager.py --search "timeout"

# 添加新经验（交互式）
python scripts/experience_manager.py --add

# 导出为Markdown
python scripts/experience_manager.py --export experiences.md
```

### 已有经验

| ID | 问题 | 解决方案 |
|----|------|----------|
| 001 | H3C使用exec_command超时 | 使用invoke_shell() |
| 002 | 配置显示不完整 | 自动处理分页 |
| 003 | Windows编码错误 | 使用errors='ignore' |
| 004 | save命令执行失败 | 自动添加force参数 |

## 参考文档

### 厂商命令对照表
查看 `references/vendor_commands.md` 获取：
- 各厂商基础命令对照
- 配置模式差异
- 常用查询命令
- 厂商特定功能命令

### 故障排查指南
查看 `references/troubleshooting_guide.md` 获取：
- 常见网络故障诊断流程
- 逐层排查方法（物理层→数据链路层→网络层）
- 日志分析技巧
- 性能瓶颈定位

### 巡检检查清单
查看 `references/inspection_checklist.md` 获取：
- 各厂商标准巡检项目
- 检查项的优先级分类
- 异常阈值定义
- 巡检周期建议

## 使用示例

### 场景1: 资产台账管理（首次使用）
```
用户: 添加一台新的核心交换机到资产台账
操作: python scripts/asset_manager.py add
     交互式输入设备信息（IP、类型、用户名等）
     系统自动保存到 assets/inventory.yaml
```

### 场景2: 通过资产台账快速连接
```
用户: 查询H3C核心交换机的版本信息
操作: python scripts/h3c_executor.py --device 核心交换机-01 --commands "display version"
     系统自动从资产台账查找并获取连接信息
     直接建立连接并执行命令
```

### 场景3: 单设备配置查询
```
用户: 查询交换机192.168.1.1的所有接口状态
操作: python scripts/huawei_executor.py --device 192.168.1.1 --commands "display interface brief"
     系统从台账自动匹配设备并连接
     执行命令并返回结果
```

### 场景4: 设备健康巡检
```
用户: 对核心交换机进行健康检查
操作: python scripts/health_check.py
     连接设备后执行全面检查
     生成巡检报告
```

### 场景5: 批量配置备份
```
用户: 备份所有核心分组交换机配置
操作: python scripts/batch_manager.py core
     批量执行config_backup.py
     按日期归档备份文件
```

### 场景6: 查找并管理资产
```
用户: 查找所有位于机房A的设备
操作: python scripts/asset_manager.py find 机房A
```

### 场景7: 故障应急处理
```
用户: 核心链路中断，快速诊断问题
操作: python scripts/h3c_executor.py --device 核心交换机-01 --commands "display interface brief" "display ip routing-table"
     使用troubleshooting_guide.md指导排查流程
     逐层检查物理链路→接口状态→路由→邻居关系
```

### 场景8: 查询命令帮助（命令语法不确定时）
```
用户: 不确定如何正确删除NAT映射
操作: python scripts/h3c_executor.py --host 10.0.254.2 --username admin --password xxx \
       --query-help "undo nat server protocol tcp global current-interface"
     返回命令语法和可选参数，帮助生成正确的命令
```

### 场景9: 自动帮助模式（命令失败时自动查询）
```
用户: 执行可能出错的命令，需要自动获取帮助信息
操作: python scripts/h3c_executor.py --host 10.0.254.2 --username admin --password xxx \
       --commands "display nat xxxx" --auto-help
     命令失败时自动查询帮助，在返回结果的 help 字段中包含语法提示
```

## 技术依赖

所有脚本依赖以下Python库：
- **Paramiko**: 底层SSH协议实现
- **PyYAML**: 配置文件解析
- **Rich**: 终端输出美化（可选）

安装依赖：
```bash
pip install paramiko pyyaml rich
```

## 最佳实践

1. **安全性**
   - 不要在脚本中硬编码密码
   - 使用交互式输入或加密的配置文件
   - 敏感操作前先备份配置

2. **可靠性**
   - 执行变更前使用 `show run/display current-configuration` 备份
   - 批量操作前先在单台设备测试
   - 配置变更后保存配置（write/save）

3. **可追溯性**
   - 所有操作记录日志（时间、设备、命令、结果）
   - 配置备份按版本管理
   - 巡检报告归档保存

4. **错误处理**
   - 网络连接失败自动重试（最多3次）
   - 命令执行失败记录详细错误信息
   - 批量操作失败不影响其他设备

## 限制说明

- Telnet和串口连接安全性较低，建议仅在管理网络内使用
- 不同厂商、不同版本的命令语法可能有差异，执行器会尽量适配
- 某些厂商特定功能可能需要手动操作
- 生产环境变更操作前务必在测试环境验证
