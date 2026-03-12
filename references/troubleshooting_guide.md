# 网络设备故障排查指南

本指南提供网络设备常见问题的系统化诊断流程和解决方案。

## 目录

- [排查方法论](#排查方法论)
- [SSH连接问题](#ssh连接问题)
- [物理层问题](#物理层问题)
- [链路层问题](#链路层问题)
- [网络层问题](#网络层问题)
- [性能问题](#性能问题)
- [安全相关](#安全相关)
- [日志分析](#日志分析)

---

## 排查方法论

### 逐层排查法

按照OSI七层模型从底层向上逐层排查：

```
物理层 (Layer 1)
    ↓
数据链路层 (Layer 2)
    ↓
网络层 (Layer 3)
    ↓
传输层 (Layer 4)
    ↓
应用层 (Layer 5-7)
```

### 问题定义模板

在开始排查前，明确以下信息：

- **问题描述**: 具体现象是什么？
- **影响范围**: 单个设备、多个设备还是全网？
- **发生时间**: 何时开始出现问题？
- **变更记录**: 最近是否有配置变更？
- **报错信息**: 有什么错误提示？

---

## SSH连接问题

SSH连接是网络自动化运维的基础，以下是基于实际经验的SSH连接问题排查指南。

### 常见问题

#### 1. 认证超时 (Authentication Timeout)

**症状**:
```
paramiko.ssh_exception.AuthenticationException: Authentication timeout.
netmiko.exceptions.NetmikoAuthenticationException: Authentication to device failed.
```

**可能原因**:
- 密码错误
- 用户名错误
- SSH服务配置问题
- 账户被锁定

**排查步骤**:

1. **验证网络连通性**
```bash
ping <设备IP>
telnet <设备IP> 22  # 检查SSH端口
```

2. **手动SSH验证**
```bash
ssh admin@<设备IP>
# 手动输入密码测试
```

3. **检查设备SSH配置**
```bash
# H3C设备
display ssh server status

# 思科设备
show ssh
show ip ssh
```

4. **检查账户状态**
```bash
# 查看当前登录用户
display users  # H3C
show users    # 思科
```

**解决方案**:
- 确认用户名和密码完全正确（区分大小写）
- 检查是否需要enable密码
- 尝试重置密码
- 检查设备SSH日志

---

#### 2. 命令执行超时 (TimeoutError on exec_command)

**症状**:
```
TimeoutError: [Errno 60] Connection timed out
或在执行命令时长时间无响应
```

**特别说明**: 这是H3C Comware V7设备的常见问题！

**原因分析**:
- H3C Comware V7对SSH exec_command支持不完善
- 设备SSH服务器实现与标准SSH协议有差异
- exec_command通道处理方式不同

**解决方案**:

**✓ 方案1: 使用invoke_shell()（强烈推荐）**

```python
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.connect(hostname, username=username, password=password)

# 创建交互式shell
shell = ssh.invoke_shell()
time.sleep(1)

# 发送命令
shell.send('display version\n')
time.sleep(2)

# 接收输出
output = shell.recv(65535).decode('utf-8', errors='ignore')
print(output)
```

**✗ 避免使用exec_command()**:
```python
# 这种方式在H3C设备上容易超时
stdin, stdout, stderr = ssh.exec_command('display version')
```

---

#### 3. 配置显示不完整（分页问题）

**症状**:
- 只获取到部分配置
- 输出包含"---- More ----"提示符
- 配置被截断

**原因**:
H3C设备默认分页显示，每屏24行后显示"---- More ----"

**解决方案**:

**方法1: 自动发送空格继续**

```python
def send_command_with_pagination(shell, command, timeout=60):
    shell.send(command + '\n')

    output = ""
    start_time = time.time()

    while time.time() - start_time < timeout:
        if shell.recv_ready():
            chunk = shell.recv(65535).decode('utf-8', errors='ignore')
            output += chunk

            # 检测分页提示符
            if "---- More ----" in chunk:
                shell.send(" ")  # 发送空格继续
                time.sleep(0.3)
                continue

            # 检测命令完成
            if re.search(r'<\w+>', chunk) and len(output) > len(command):
                time.sleep(0.5)
                if not shell.recv_ready():
                    break

        time.sleep(0.2)

    return output
```

**方法2: 禁用分页（如果设备支持）**

```bash
# H3C设备（进入系统视图后）
undo pager
# 或
screen-length disable
```

---

#### 4. Windows编码错误

**症状**:
```
UnicodeEncodeError: 'gbk' codec can't encode character '\u2713' in position 0
```

**原因**:
Windows控制台默认使用GBK编码，不支持某些Unicode字符

**解决方案**:

**方法1: 使用简单输出**
```python
# ✓ 使用简单文本
print("[OK] Connection successful")
print("[ERROR] Connection failed")

# ✗ 避免特殊Unicode字符
console.print("✓ Connection successful")  # ✓字符会出错
```

**方法2: 使用errors='ignore'**
```python
output = shell.recv(65535).decode('utf-8', errors='ignore')
```

**方法3: 设置环境变量**
```bash
set PYTHONIOENCODING=utf-8
python script.py
```

---

#### 5. SSH连接建立但命令无响应

**症状**:
- SSH连接成功
- 发送命令后无输出
- 或输出只有命令回显

**可能原因**:
- Shell未完全初始化
- 发送命令太快
- 特权模式未进入

**解决方案**:

```python
# 等待shell完全启动
shell = ssh.invoke_shell()
time.sleep(2)  # 给足够时间

# 清空初始缓冲区
if shell.recv_ready():
    shell.recv(65535)

# 发送命令
shell.send('display version\n')
time.sleep(2)  # 等待命令执行

# 接收输出
output = ""
while shell.recv_ready():
    output += shell.recv(65535).decode('utf-8', errors='ignore')
    time.sleep(0.5)
```

---

### H3C设备连接最佳实践

基于实际测试经验，以下是H3C设备连接的推荐做法：

#### 推荐配置

```python
import paramiko
import time
import re

def connect_h3c(host, username, password):
    """H3C设备可靠连接方法"""

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # 增加超时时间
        ssh.connect(
            hostname=host,
            port=22,
            username=username,
            password=password,
            timeout=30,
            auth_timeout=30,
            banner_timeout=30,
            allow_agent=False,
            look_for_keys=False
        )

        # 使用invoke_shell而不是exec_command
        shell = ssh.invoke_shell()
        time.sleep(2)  # 等待shell初始化

        # 清空初始输出
        if shell.recv_ready():
            shell.recv(65535)

        return shell

    except Exception as e:
        print(f"连接失败: {str(e)}")
        return None
```

#### 完整示例脚本

参考 `scripts/h3c_get_full_config.py` 获取完整的、经过测试的代码。

**使用方法**:
```bash
python scripts/h3c_get_full_config.py <密码>
```

---

### 连接诊断流程图

```
开始
  ↓
Ping设备 → 失败 → 检查网络
  ↓ 成功
检查SSH端口 → 失败 → 检查SSH服务
  ↓ 成功
尝试手动SSH → 失败 → 检查凭据
  ↓ 成功
使用invoke_shell → 成功 → 正常使用
  ↓ 失败
增加超时时间
  ↓
添加编码处理
  ↓
处理分页
  ↓
成功
```

---

### 快速诊断命令

| 测试项 | 命令 | 预期结果 |
|--------|------|----------|
| 网络连通 | `ping <IP>` | 通，<1ms延迟 |
| SSH端口 | `telnet <IP> 22` 或 `nc -zv <IP> 22` | 端口开放 |
| 手动SSH | `ssh admin@<IP>` | 可以登录 |
| Python测试 | `python scripts/simple_h3c_connect.py` | 连接成功 |

---

## 物理层问题

### 症状

- 接口显示down状态
- 链路不通
- 指示灯异常

### 检查步骤

#### 1. 检查接口状态

**华为/H3C:**
```bash
display interface <interface-name>
display interface brief
```

**思科:**
```bash
show interface <interface-name>
show ip interface brief
```

**锐捷:**
```bash
show interface <interface-name>
show interface status
```

#### 2. 检查物理连接

- 确认网线/光纤连接正常
- 检查接口指示灯状态
- 确认模块/SFP插入正确
- 测试更换线缆或接口

#### 3. 检查接口配置

确认接口没有被管理性关闭：

**华为/H3C:**
```bash
# 检查是否有 shutdown
display current-configuration | include <interface-name>

# 恢复接口
interface <interface-name>
undo shutdown
```

**思科:**
```bash
# 检查配置
show running-config interface <interface-name>

# 恢复接口
interface <interface-name>
no shutdown
```

#### 4. 检查双工/速率匹配

```bash
# 华为/H3C
display interface <interface-name> | include Duplex

# 思科
show interface <interface-name> | include Duplex
```

**解决方案**: 确保两端双工模式和速率一致，建议都设为auto或都指定固定值。

---

## 链路层问题

### 症状

- 接口up但协议down
- MAC地址学习异常
- VLAN不通
- 生成树环路

### 检查步骤

#### 1. 检查VLAN配置

```bash
# 华为/H3C
display vlan
display port vlan

# 思科
show vlan brief
show interfaces switchport

# 锐捷
show vlan
show interfaces switchport
```

#### 2. 检查Trunk配置

确认Trunk允许的VLAN列表正确：

```bash
# 华为
display current-configuration interface <interface-name> | include trunk

# 思科
show interfaces <interface-name> switchport
```

#### 3. 检查生成树状态

```bash
# 华为/H3C
display stp
display stp brief

# 思科
show spanning-tree
show spanning-tree summary
```

#### 4. 检查MAC地址表

```bash
# 华为/H3C
display mac-address
display mac-address dynamic <interface-name>

# 思科
show mac address-table
show mac address-table dynamic interface <interface-name>
```

#### 5. 检测环路

**症状**:
- MAC地址表震荡
- CPU使用率高
- 广播风暴

**解决方案**:
- 检查生成树配置
- 启用环路检测功能
- 排查物理连接

---

## 网络层问题

### 症状

- 路由不可达
- 路由表缺失
- ARP解析失败
- 网络不通但接口正常

### 检查步骤

#### 1. 检查路由表

```bash
# 华为/H3C
display ip routing-table
display ip routing-table <destination-ip>

# 思科
show ip route
show ip route <destination-ip>

# 锐捷
show ip route
```

**关注点**:
- 是否存在到目的网络的路由
- 路由是否是最佳路径
- 路由是否失效（down状态）

#### 2. 检查ARP表

```bash
# 华为/H3C
display arp
display arp | include <ip-address>

# 思科
show ip arp
show ip arp | include <ip-address>

# 锐捷
show arp
```

**常见问题**:
- ARP未解析：检查二层连通性
- ARP错误：检查IP地址冲突

#### 3. Ping测试

```bash
# 本地接口
ping <local-interface-ip>

# 网关
ping <gateway-ip>

# 目的主机
ping <destination-ip>

# 扩展ping（源地址指定）
ping -a <source-ip> <destination-ip>
```

#### 4. Traceroute

```bash
# 华为/H3C
tracert <destination-ip>

# 思科
traceroute <destination-ip>

# 锐捷
traceroute <destination-ip>
```

**分析**: 确定在哪一跳路径中断

#### 5. 检查路由协议

**OSPF:**
```bash
# 华为/H3C
display ospf peer
display ospf routing

# 思科
show ip ospf neighbor
show ip ospf route
```

**BGP:**
```bash
# 华为/H3C
display bgp peer
display bgp routing-table

# 思科
show ip bgp summary
show ip bgp
```

---

## 性能问题

### 症状

- 网络缓慢
- 高CPU/内存使用率
- 丢包
- 延迟高

### 检查步骤

#### 1. 检查CPU和内存

```bash
# 华为/H3C
display cpu-usage
display memory-usage

# 思科
show processes cpu
show memory statistics

# 锐捷
show cpu
show memory
```

**阈值参考**:
- CPU > 80%: 需要关注
- CPU > 90%: 严重
- 内存 > 85%: 需要关注

#### 2. 检查接口流量和错误

```bash
# 华为/H3C
display interface <interface-name> | include rate
display interface <interface-name> | include error

# 思科
show interface <interface-name> | include rate
show interface <interface-name> | include error
```

**关注指标**:
- 输入/输出速率接近带宽上限
- CRC错误（物理问题）
- 丢包计数（buffer不足）
- 冲突计数（双工不匹配）

#### 3. 检查队列和buffer

```bash
# 华为/H3C
display queue-statistics

# 思科
show queueing
show buffers
```

#### 4. 性能优化建议

- 启用QoS保证关键业务
- 调整接口MTU
- 优化路由策略
- 升级带宽

---

## 安全相关

### 症状

- 无法登录
- 登录后立即断开
- ACL阻断流量
- 安全策略问题

### 检查步骤

#### 1. 检查ACL配置

```bash
# 华为/H3C
display acl all
display packet-filter <interface-name>

# 思科
show access-lists
show ip access-lists

# 锐捷
show access-lists
```

#### 2. 检查登录限制

```bash
# 华为/H3C
display users
display aaa configuration

# 思科
show users
show running-config | include login
```

#### 3. 检查安全策略

```bash
# 华为/H3C
display firewall session all
display security-policy

# 思科
show ip inspect sessions
```

---

## 日志分析

### 查看日志

```bash
# 华为/H3C
display logbuffer
display logbuffer reverse  | include error

# 思科
show logging
show logging | include error
```

### 常见错误关键字

- **Link down/up**: 链路振荡
- **Flapping**: 接口频繁up/down
- **Loopback detected**: 检测到环路
- **Packet discarded**: 丢包
- **Authentication failed**: 认证失败
- **ACL deny**: ACL拒绝
- **Memory low**: 内存不足

### 日志级别

- **Emergency (0)**: 系统不可用
- **Alert (1)**: 需要立即采取行动
- **Critical (2)**: 严重情况
- **Error (3)**: 错误情况
- **Warning (4)**: 警告情况
- **Notification (5)**: 正常但重要
- **Informational (6)**: 信息性消息
- **Debug (7)**: 调试信息

---

## 快速诊断检查清单

### 第一步：基础检查

- [ ] 设备电源正常
- [ ] 指示灯状态正常
- [ ] 线缆连接牢固
- [ ] 接口状态为up
- [ ] 配置最近无变更

### 第二步：连通性检查

- [ ] 接口协议状态up
- [ ] VLAN配置正确
- [ ] 路由表存在
- [ ] ARP解析成功
- [ ] Ping测试通

### 第三步：性能检查

- [ ] CPU使用率正常
- [ ] 内存使用率正常
- [ ] 接口无大量错误
- [ ] 无丢包现象
- [ ] 无环路

### 第四步：日志检查

- [ ] 无严重错误
- [ ] 无安全告警
- [ ] 无硬件故障
- [ ] 配置变更记录

---

## 常用诊断命令组合

### 综合检查脚本

**华为/H3C:**
```bash
# 系统信息
display version
# 接口状态
display interface brief
# 路由表
display ip routing-table
# ARP表
display arp
# CPU内存
display cpu-usage
display memory-usage
# 日志
display logbuffer reverse | include error
```

**思科:**
```bash
# 系统信息
show version
# 接口状态
show ip interface brief
# 路由表
show ip route
# ARP表
show ip arp
# CPU内存
show processes cpu
show memory statistics
# 日志
show logging | include error
```

---

## 应急处理流程

### 核心链路中断

1. **立即**: 检查物理连接和接口状态
2. **快速**: Ping上下游设备定位故障点
3. **分析**: 查看路由和配置
4. **恢复**: 尝试切换到备用路径
5. **根因**: 事后分析日志定位原因

### 设备CPU过高

1. **排查**: 查看进程占用情况
2. **隔离**: 确定是否是攻击或环路
3. **处理**: 关闭非必要服务
4. **监控**: 持续观察CPU变化

### 网络环路

1. **识别**: MAC地址表震荡、CPU高
2. **定位**: Traceroute确定环路位置
3. **解决**: 检查生成树配置
4. **预防**: 启用环路检测

---

## 寻求帮助

当问题无法自行解决时，准备以下信息寻求帮助：

1. 设备型号和软件版本
2. 详细的问题描述和影响范围
3. 相关配置（脱敏后）
4. 诊断命令输出
5. 故障发生时间线
6. 已尝试的解决步骤
