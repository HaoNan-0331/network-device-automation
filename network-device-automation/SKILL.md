---
name: network-device-automation
description: 网络设备运维自动化技能。此技能应在需要对网络设备（华为、H3C、思科、锐捷等）进行运维操作时使用，包括SSH/Telnet/串口连接、配置管理、故障诊断、健康巡检、批量操作等场景。支持交互式输入连接信息，适用于日常运维、批量管理、故障应急处理和自动化巡检任务。
---

# 网络设备运维自动化技能

本技能提供网络设备自动化运维能力，支持主流网络设备厂商的统一管理。

## 技能用途

本技能用于网络设备的自动化运维操作，包括但不限于：
- 设备连接管理（SSH/Telnet/串口）
- 配置查询、备份和恢复
- 设备健康检查和巡检
- 故障诊断和应急处理
- 批量设备操作

## 支持的设备厂商

- 华为 (Huawei)
- 华三 (H3C)
- 思科 (Cisco)
- 锐捷 (Ruijie)
- 其他支持标准CLI的设备

## 资产台账功能

本技能集成了资产台账功能，支持提前录入设备信息，使用时自动查找匹配。

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

### 设备连接集成

设备连接时优先从资产台账查找，支持多种匹配方式：

```bash
# 方式1: 直接使用设备IP查找
python scripts/device_connector.py 192.168.1.1

# 方式2: 使用设备名称查找
python scripts/device_connector.py 核心交换机-01

# 方式3: 使用--find参数
python scripts/device_connector.py --find core-sw-01

# 方式4: 列出所有设备
python scripts/device_connector.py --list
```

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

### 密码安全策略

- 密码使用 **base64 编码**存储（基础加密）
- **推荐做法**: 敏感设备的密码字段留空，使用时交互式输入
- 密码为空时，系统会提示用户输入密码
- 生产环境建议定期更换密码

### 使用工作流程

1. **首次使用**: 添加设备到资产台账
   ```bash
   python scripts/asset_manager.py add
   ```

2. **日常使用**: 直接通过IP/名称连接，系统自动查找
   ```bash
   python scripts/device_connector.py 192.168.1.1
   ```

3. **设备未找到**: 系统询问是否要添加新设备
   - 选择是：进入添加流程
   - 选择否：使用交互式输入连接

## 核心工作流程

### 1. 设备连接

使用交互式输入方式获取设备连接信息：

```python
python scripts/device_connector.py
```

连接方式支持：
- **SSH** (推荐): 使用 Netmiko 库实现跨厂商SSH连接
- **Telnet**: 用于不支持SSH的 legacy 设备
- **串口**: 通过 console 线连接本地设备

连接时需要提供：
- 设备IP或主机名
- 设备类型（厂商/型号）
- 用户名和密码
- 端口（SSH默认22，Telnet默认23）
- enable密码（如需要）

### 2. 命令执行

执行单条或多条配置/查询命令：

```python
python scripts/command_executor.py
```

特性：
- 自动识别设备厂商并适配命令语法
- 支持配置模式切换
- 支持命令输出结构化解析
- 支持批量命令执行和结果汇总

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

设备清单使用YAML格式定义，参考模板：`assets/templates/inventory_template.yaml`

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
用户: 连接到核心交换机-01
操作: python scripts/device_connector.py 核心交换机-01
     系统自动从资产台账查找并获取连接信息
     直接建立连接（密码已存储）或提示输入密码
```

### 场景3: 单设备配置查询（使用台账）
```
用户: 查询交换机192.168.1.1的所有接口状态
操作: python scripts/device_connector.py 192.168.1.1
     系统从台账自动匹配设备并连接
     使用command_executor.py执行display interfaces/show ip interface brief
     解析并格式化输出
```

### 场景4: 设备健康巡检
```
用户: 对核心交换机进行健康检查
操作: python scripts/device_connector.py 核心交换机-01
     使用health_check.py执行全面检查
     生成巡检报告（使用report_template.md格式）
```

### 场景5: 批量配置备份（使用台账）
```
用户: 备份所有核心分组交换机配置
操作: python scripts/batch_manager.py core
     批量执行config_backup.py
     按日期归档备份文件
```

### 场景6: 查找并管理资产
```
用户: 查找所有位于机房A的设备
操作: python scripts/asset_manager.py list | grep 机房A
     或: python scripts/asset_manager.py find 机房A
```

### 场景7: 故障应急处理（使用台账）
```
用户: 核心链路中断，快速诊断问题
操作: python scripts/device_connector.py 核心交换机-01
     使用troubleshooting_guide.md指导排查流程
     逐层检查物理链路→接口状态→路由→邻居关系
     定位根因并提供恢复建议
```

## 技术依赖

所有脚本依赖以下Python库：
- **Netmiko**: 跨厂商SSH连接管理
- **Paramiko**: 底层SSH协议实现
- **PyYAML**: 配置文件解析
- **Rich**: 终端输出美化（可选）

安装依赖：
```bash
pip install netmiko paramiko pyyaml rich
```

## 最佳实践

1. **安全性**
   - 不要在脚本中硬编码密码
   - 使用交互式输入或加密的配置文件
   - 敏感操作前先备份配置

2. **可靠性**
   - 执行变更前使用`show run/display current-configuration`备份
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

## H3C设备连接特别说明

### 重要经验总结

基于实际测试经验，H3C设备（特别是Comware V7版本）连接时需要注意以下关键点：

### 1. 连接方法选择

**推荐使用 invoke_shell() 而非 exec_command()**

```python
# ✓ 推荐方式 - 使用交互式shell
shell = ssh.invoke_shell()
shell.send('display version\n')
output = shell.recv(65535).decode('utf-8', errors='ignore')

# ✗ 不推荐 - exec_command可能超时
stdin, stdout, stderr = ssh.exec_command('display version')
```

**原因**:
- H3C Comware V7的SSH服务器对exec_command支持不完善
- exec_command在执行命令时容易出现TimeoutError
- invoke_shell模拟真实终端会话，更稳定可靠

### 2. 分页处理

H3C设备默认使用分页显示（每屏24行后显示"---- More ----"），需要自动处理：

```python
# 检测分页提示符并自动发送空格
if "---- More ----" in chunk:
    shell.send(" ")  # 发送空格继续
    time.sleep(0.3)
```

**参考脚本**: `scripts/h3c_get_full_config.py` - 已实现自动分页处理

### 3. 设备类型映射

```python
H3C设备使用 'hp_comware' 作为device_type：
connection = ConnectHandler(
    host='192.168.56.2',
    device_type='hp_comware',  # H3C使用此类型
    username='admin',
    password='your_password'
)
```

### 4. 超时设置

H3C设备需要较长的超时时间：

```python
ssh.connect(
    hostname=host,
    username=username,
    password=password,
    timeout=30,         # 连接超时
    auth_timeout=30,    # 认证超时
    banner_timeout=30   # Banner超时
)
```

### 5. 编码处理

H3C设备输出可能包含特殊字符，需要使用errors='ignore'：

```python
output = shell.recv(65535).decode('utf-8', errors='ignore')
```

### 6. Windows平台注意事项

在Windows平台上避免使用Rich库的特殊Unicode字符：

```python
# ✓ 简单输出，避免编码问题
print("[OK] 连接成功")

# ✗ 可能导致GBK编码错误
console.print("✓ 连接成功")  # 包含Unicode特殊字符
```

### 7. 完整的H3C连接示例

参考 `scripts/h3c_get_full_config.py` 获取完整的、经过测试的H3C连接代码。

**使用方法**:
```bash
python scripts/h3c_get_full_config.py <密码>
```

**功能**:
- 自动处理SSH连接
- 自动处理分页显示
- 获取系统信息、接口状态、VLAN配置
- 获取完整运行配置
- 保存到文件并生成统计报告

### 8. 诊断工具

如遇到连接问题，使用诊断脚本获取详细信息：

```bash
# 1. 基础连接测试
python scripts/simple_h3c_connect.py <密码>

# 2. Shell模式连接（推荐）
python scripts/h3c_shell_connect.py <密码>

# 3. 完整配置获取
python scripts/h3c_get_full_config.py <密码>
```

### 9. 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| Authentication timeout | 密码错误或SSH配置问题 | 验证凭据，检查设备SSH配置 |
| TimeoutError on exec_command | H3C不支持exec_command | 使用invoke_shell方法 |
| 配置显示不完整 | 分页未处理 | 实现自动发送空格逻辑 |
| 编码错误 | Windows GBK限制 | 使用errors='ignore'或避免特殊字符 |

### 10. 测试验证

以下配置已验证可用：
- **设备**: H3C S6850
- **软件版本**: Comware 7.1.070, Alpha 7170
- **连接方式**: SSH (端口22)
- **认证方式**: 密码认证
- **Python版本**: 3.14
- **依赖库**: paramiko 4.0.0

### 关键要点

✅ **必须使用 invoke_shell()**
✅ **必须处理分页 ("---- More ----")**
✅ **必须设置足够的超时时间 (30秒+)**
✅ **必须使用 errors='ignore' 处理编码**
✅ **推荐使用测试验证的脚本模板**

## 限制说明

- Telnet和串口连接安全性较低，建议仅在管理网络内使用
- 不同厂商、不同版本的命令语法可能有差异，脚本会尽量适配
- 某些厂商特定功能可能需要手动操作
- 生产环境变更操作前务必在测试环境验证
