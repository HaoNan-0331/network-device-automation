# 网络设备运维自动化 - 快速开始指南

## 概述

本技能通过**厂商专属执行器**实现网络设备的自动化运维。每个厂商（H3C、华为、思科、锐捷）都有独立的执行器，支持逐条执行命令，遇错自动中断。

## 快速开始（3步）

### 步骤1: 安装依赖

```bash
pip install paramiko pyyaml rich
```

### 步骤2: 添加设备到资产台账（推荐）

```bash
cd skills/network-device-automation
python scripts/asset_manager.py add
```

按提示输入设备信息：
- 设备ID: `core-sw-01`（唯一标识符）
- 设备名称: `核心交换机-01`
- IP地址: `192.168.1.1`
- 设备类型: `hp_comware`（H3C设备）
- 用户名: `admin`
- 密码:（留空表示使用时输入，或输入密码）

### 步骤3: 执行命令

```bash
# H3C设备
python scripts/h3c_executor.py --device 核心交换机-01 --commands "display version"

# 华为设备
python scripts/huawei_executor.py --device 核心交换机-01 --commands "display version"

# 思科设备
python scripts/cisco_executor.py --device 核心交换机-01 --commands "show version"

# 锐捷设备
python scripts/ruijie_executor.py --device 核心交换机-01 --commands "show version"
```

**可选：** 查询命令帮助或启用自动帮助

```bash
# 查询命令语法帮助
python scripts/h3c_executor.py --host 10.0.254.2 --username admin --password xxx \
  --query-help "undo nat server protocol tcp global current-interface"

# 命令失败时自动查询帮助
python scripts/h3c_executor.py --host 10.0.254.2 --username admin --password xxx \
  --commands "display version" --auto-help
```

---

## 厂商执行器

### H3C执行器

```bash
# 基本用法
python scripts/h3c_executor.py --device <设备标识> --commands "<命令1>" "<命令2>"

# 示例
python scripts/h3c_executor.py --device 192.168.56.3 --commands "display version" "display vlan"

# 多条命令（含配置）
python scripts/h3c_executor.py --device 核心交换机-01 \
  --commands "system-view" "vlan 100" "quit" "save force"
```

### 华为执行器

```bash
# 基本用法
python scripts/huawei_executor.py --device <设备标识> --commands "<命令1>" "<命令2>"

# 示例
python scripts/huawei_executor.py --device 192.168.1.1 --commands "display version" "display interface brief"
```

### 思科执行器

```bash
# 基本用法
python scripts/cisco_executor.py --device <设备标识> --commands "<命令1>" "<命令2>"

# 示例
python scripts/cisco_executor.py --device 192.168.1.1 --commands "show version" "show vlan brief"

# 带enable密码
python scripts/cisco_executor.py --device 核心交换机-01 \
  --commands "show running-config" --enable-password xxx
```

### 锐捷执行器

```bash
# 基本用法
python scripts/ruijie_executor.py --device <设备标识> --commands "<命令1>" "<命令2>"

# 示例
python scripts/ruijie_executor.py --device 192.168.1.1 --commands "show version" "show interface status"
```

---

## 命令行参数

### 通用参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--device` | 设备标识符（IP/名称/ID），从资产台账查找 | `--device 192.168.1.1` |
| `--host` | 设备IP地址（降级使用） | `--host 192.168.1.1` |
| `--username` | 用户名 | `--username admin` |
| `--password` | 密码（不指定则交互式输入） | `--password xxx` |
| `--port` | SSH端口（默认22） | `--port 22` |
| `--enable-password` | Enable密码（思科/锐捷） | `--enable-password xxx` |

### 命令参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--commands` | 命令列表 | `--commands "show version" "show vlan"` |
| `--commands-json` | 从JSON读取命令（-表示标准输入） | `--commands-json commands.json` |

### 执行选项

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--timeout` | 命令超时时间（秒） | 30 |
| `--continue-on-error` | 遇错继续执行 | 遇错停止 |
| `--output` | 输出结果到文件（JSON格式） | 标准输出 |
| `--query-help` | 查询指定命令的帮助信息 | - |
| `--auto-help` | 命令失败时自动查询帮助 | 关闭 |

---

## 使用方式对比

### 方式1: 从资产台账查找（推荐）

```bash
# 优点：简洁、节省token
python scripts/h3c_executor.py --device 核心交换机-01 --commands "display version"
```

**适用场景：** 日常操作，设备已录入台账

### 方式2: 显式指定连接参数

```bash
# 优点：无需提前录入
python scripts/h3c_executor.py --host 192.168.56.3 --username admin --password xxx --commands "display version"
```

**适用场景：** 临时操作，设备未录入台账

### 方式3: 从JSON文件读取命令

```bash
# 创建命令文件
echo '["display version", "display vlan", "display interface brief"]' > commands.json

# 执行
python scripts/h3c_executor.py --device 192.168.56.3 --commands-json commands.json
```

**适用场景：** 批量命令执行

### 方式4: 标准输入

```bash
echo '["display version", "display vlan"]' | python scripts/h3c_executor.py --device 192.168.56.3 --commands-json -
```

**适用场景：** 脚本/管道集成

---

## 执行器返回格式

所有执行器统一返回JSON格式：

```json
{
  "success": true,
  "executed": 2,
  "total": 2,
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
      "success": true,
      "output": "VLAN ID: 1...",
      "error": null,
      "help": null
    }
  ]
}
```

**返回字段说明：**

| 字段 | 说明 |
|------|------|
| `success` | 整体是否成功（所有命令都成功） |
| `executed` | 已执行的命令数 |
| `total` | 总命令数 |
| `failed_at` | 失败位置（从1开始，null表示无失败） |
| `results` | 每条命令的执行结果 |
| `results[].command` | 执行的命令 |
| `results[].success` | 该命令是否成功 |
| `results[].output` | 命令输出 |
| `results[].error` | 错误信息（如有） |
| `results[].help` | 帮助信息（使用 `--auto-help` 时自动获取） |

---

## 常见问题

### Q1: 如何查找设备？

```bash
# 查看所有设备
python scripts/asset_manager.py list

# 查找设备
python scripts/asset_manager.py find 192.168.1.1
python scripts/asset_manager.py find 核心交换机
```

### Q2: 密码未存储怎么办？

```bash
# 执行时会提示输入密码
python scripts/h3c_executor.py --device 核心交换机-01 --commands "display version"
> 密码: *****
```

### Q3: 命令执行失败如何处理？

执行器会遇错自动中断并返回错误信息：

```json
{
  "success": false,
  "executed": 2,
  "total": 3,
  "failed_at": 3,
  "results": [
    ...
    {
      "command": "display xxxx",
      "success": false,
      "error": "命令执行错误: Unrecognized command"
    }
  ]
}
```

### Q4: 如何保存执行结果？

```bash
# 保存到文件
python scripts/h3c_executor.py --device 192.168.56.3 --commands "display version" --output result.json
```

### Q5: 设备台账中没有的设备如何处理？

```bash
# 方式1: 先添加到台账
python scripts/asset_manager.py add

# 方式2: 直接使用显式参数
python scripts/h3c_executor.py --host 192.168.56.3 --username admin --password xxx --commands "display version"
```

### Q6: 如何查询命令帮助（不确定命令语法时）？

```bash
# 查询特定命令的帮助
python scripts/h3c_executor.py --host 10.0.254.2 --username admin --password xxx \
  --query-help "undo nat server protocol tcp global current-interface"

# 返回结果会显示该命令的语法和可用参数
```

### Q7: 如何让命令失败时自动查询帮助？

```bash
# 启用 --auto-help 参数
python scripts/h3c_executor.py --host 10.0.254.2 --username admin --password xxx \
  --commands "display version" "可能出错的命令" --auto-help

# 当命令失败时，返回结果的 help 字段会包含帮助信息
```

---

## Token节省对比

| 方式 | Token消耗 | 说明 |
|------|-----------|------|
| **使用--device** | ~20 token | 从资产台账查找，自动填充连接参数 |
| **使用--host/--username** | ~100 token | 需要显式指定所有连接参数 |

**建议：** 日常操作优先使用 `--device` 从台账查找，节省约80%的token。

---

## 下一步

- 查看完整文档：[SKILL.md](SKILL.md)
- 查看资产台账指南：[ASSET_LEDGER_GUIDE.md](ASSET_LEDGER_GUIDE.md)
- 查看厂商命令对照：[references/vendor_commands.md](references/vendor_commands.md)
