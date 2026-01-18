# 网络设备资产台账快速使用指南

## 概述

资产台账是 network-device-automation 技能的核心功能之一，允许你提前录入设备信息，在执行运维操作时自动查找并连接设备，极大提升工作效率。

## 快速开始

### 1. 添加第一台设备

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
- 分组: `core`

### 2. 查看所有设备

```bash
python scripts/asset_manager.py list
```

输出示例：
```
┏━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ ID     ┃ 名称             ┃ IP/主机名      ┃
┡━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ core-...│ 核心交换机-01    │ 192.168.1.1    │
└────────┴──────────────────┴────────────────┘
```

### 3. 快速连接设备

```bash
# 方式1: 使用IP
python scripts/device_connector.py 192.168.1.1

# 方式2: 使用设备名称
python scripts/device_connector.py 核心交换机-01

# 方式3: 使用设备ID
python scripts/device_connector.py core-sw-01
```

### 4. 查找特定设备

```bash
# 按IP查找
python scripts/asset_manager.py find 192.168.1.1

# 按名称查找
python scripts/asset_manager.py find 核心交换机

# 模糊搜索
python scripts/asset_manager.py find 机房A
```

## 常用命令速查

| 命令 | 说明 |
|------|------|
| `python scripts/asset_manager.py list` | 列出所有设备 |
| `python scripts/asset_manager.py list core` | 列出特定分组的设备 |
| `python scripts/asset_manager.py find <关键词>` | 查找设备 |
| `python scripts/asset_manager.py add` | 添加新设备 |
| `python scripts/asset_manager.py update <设备ID>` | 更新设备信息 |
| `python scripts/asset_manager.py delete <设备ID>` | 删除设备 |
| `python scripts/asset_manager.py export backup.json` | 导出为JSON |
| `python scripts/asset_manager.py import backup.json` | 从JSON导入 |
| `python scripts/device_connector.py --list` | 通过连接器列出设备 |
| `python scripts/device_connector.py --add` | 通过连接器添加设备 |

## 设备匹配规则

资产台账支持智能匹配，你可以使用以下任一方式查找设备：

| 匹配方式 | 示例 | 说明 |
|----------|------|------|
| IP地址 | `192.168.1.1` | 完全匹配host字段 |
| 主机名 | `sw-core-01.example.com` | 完全匹配host字段 |
| 设备名称 | `核心交换机-01` | 完全匹配name字段 |
| 设备ID | `core-sw-01` | 完全匹配台账键名 |
| 模糊搜索 | `核心` | 部分匹配name或description |

## 密码管理策略

### 推荐做法（更安全）

敏感设备的密码字段留空：

```yaml
devices:
  core-sw-01:
    name: "核心交换机-01"
    host: "192.168.1.1"
    password: ""  # 留空
```

使用时会提示输入密码：
```bash
$ python scripts/device_connector.py 192.168.1.1
正在查找设备: 192.168.1.1
从资产台账找到设备: 核心交换机-01 (192.168.1.1)
资产中未存储密码，需要交互式输入
密码: *****
```

### 便捷做法（较方便）

非敏感设备可存储密码（base64编码）：

```yaml
devices:
  access-sw-01:
    name: "接入交换机-01"
    host: "192.168.1.10"
    password: "YWRtaW4xMjM="  # base64编码的密码
```

## 文件位置

| 文件 | 路径 |
|------|------|
| 资产台账 | `skills/network-device-automation/assets/inventory.yaml` |
| 资产管理器 | `skills/network-device-automation/scripts/asset_manager.py` |
| 设备连接器 | `skills/network-device-automation/scripts/device_connector.py` |

## 批量操作

### 按分组操作

```bash
# 备份所有核心设备
python scripts/batch_manager.py core

# 巡检所有接入设备
python scripts/batch_manager.py access --health-check
```

### 从台账生成批量清单

资产台账可与原有的 `inventory_template.yaml` 配合使用：

```bash
# 导出为批量操作格式
python scripts/asset_manager.py export batch_inventory.json
```

## 故障排查

### 问题：找不到设备

```bash
# 检查台账中是否有该设备
python scripts/asset_manager.py list | grep <关键词>

# 查看所有设备
python scripts/asset_manager.py list
```

### 问题：密码错误

```bash
# 更新设备密码
python scripts/asset_manager.py update <设备ID>
# 系统会提示输入新密码
```

### 问题：连接失败

1. 检查网络连通性：`ping <IP>`
2. 检查设备类型是否正确
3. 查看设备连接器输出

## 完整工作流程示例

```bash
# 1. 添加设备
python scripts/asset_manager.py add

# 2. 验证设备已添加
python scripts/asset_manager.py list

# 3. 测试连接
python scripts/device_connector.py <IP或名称>

# 4. 执行巡检（连接成功后）
python scripts/health_check.py

# 5. 备份配置
python scripts/config_backup.py
```

## 最佳实践

1. **设备ID命名规范**: 使用 `<角色>-<类型>-<编号>` 格式
   - 示例: `core-sw-01`, `access-rtr-02`

2. **分组管理**: 按功能或位置分组
   - 示例: `core`, `access`, `edge`, `datacenter`

3. **标签使用**: 使用标签进行多维度分类
   - 示例: `production`, `test`, `critical`, `backup`

4. **密码策略**:
   - 核心设备: 密码留空，使用时输入
   - 接入设备: 可存储密码

5. **定期备份**:
   ```bash
   python scripts/asset_manager.py export inventory_backup_$(date +%Y%m%d).json
   ```

## 扩展阅读

- [SKILL.md](SKILL.md) - 完整技能文档
- [QUICK_START.md](QUICK_START.md) - 技能快速开始指南
- [references/vendor_commands.md](references/vendor_commands.md) - 厂商命令对照
