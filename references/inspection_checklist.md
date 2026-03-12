# 网络设备巡检检查清单

本文档提供网络设备的标准巡检项目和检查标准，适用于华为、H3C、思科、锐捷等设备。

## 巡检分类

- [每日巡检](#每日巡检)
- [每周巡检](#每周巡检)
- [每月巡检](#每月巡检)
- [季度巡检](#季度巡检)

---

## 每日巡检

### 目的
快速检查设备运行状态，发现紧急问题。

### 检查项目

#### 1. 设备状态

| 检查项 | 命令 | 正常状态 | 异常阈值 | 优先级 |
|--------|------|----------|----------|--------|
| 设备运行时间 | `display version` / `show version` | 正常运行 | N/A | P1 |
| 设备温度 | `display environment` / `show environment` | 正常范围 | 超过规格 | P1 |
| 电源状态 | `display power` / `show power` | 正常供电 | 异常 | P1 |
| 风扇状态 | `display fan` / `show fan` | 正常运转 | 故障 | P1 |

**检查方法**:
```bash
# 华为/H3C
display version
display device
display environment

# 思科
show version
show environment all
```

#### 2. CPU和内存

| 检查项 | 正常阈值 | 警告阈值 | 严重阈值 | 优先级 |
|--------|----------|----------|----------|--------|
| CPU使用率 | < 70% | 70-90% | > 90% | P1 |
| 内存使用率 | < 75% | 75-85% | > 85% | P1 |

**检查方法**:
```bash
# 华为/H3C
display cpu-usage
display memory-usage

# 思科
show processes cpu
show memory statistics
```

#### 3. 接口状态

| 检查项 | 正常状态 | 异常情况 | 优先级 |
|--------|----------|----------|--------|
| 关键接口up状态 | up | down | P1 |
| 接口错误率 | < 0.1% | > 0.1% | P2 |
| 接口带宽利用率 | < 70% | > 85% | P2 |

**检查方法**:
```bash
# 华为/H3C
display interface brief
display interface <interface-name> | include error

# 思科
show ip interface brief
show interface <interface-name> | include error
```

#### 4. 日志检查

| 检查项 | 说明 | 优先级 |
|--------|------|--------|
| Emergency/Alert日志 | 系统不可用/立即行动 | P1 |
| Critical日志 | 严重情况 | P1 |
| Error日志 | 错误情况 | P2 |

**检查方法**:
```bash
# 华为/H3C
display logbuffer reverse | include error

# 思科
show logging | include error
```

---

## 每周巡检

### 目的
深入检查设备健康状况和性能趋势。

### 检查项目

#### 1. 路由协议状态

| 检查项 | 命令 | 正常状态 | 优先级 |
|--------|------|----------|--------|
| OSPF邻居 | `display ospf peer` / `show ip ospf neighbor` | Full状态 | P1 |
| BGP邻居 | `display bgp peer` / `show ip bgp summary` | Established | P1 |
| 路由表完整 | `display ip routing-table` / `show ip route` | 正常 | P1 |

**检查方法**:
```bash
# 华为/H3C
display ospf peer brief
display bgp peer

# 思科
show ip ospf neighbor
show ip bgp summary
```

#### 2. 生成树状态

| 检查项 | 正常状态 | 异常情况 | 优先级 |
|--------|----------|----------|--------|
| STP状态 | 稳定 | 频繁变化 | P1 |
| 根桥稳定 | 固定 | 变化 | P1 |
| 端口状态 | Forwarding/Blocking | Loop | P1 |

**检查方法**:
```bash
# 华为/H3C
display stp brief
display stp interface

# 思科
show spanning-tree summary
show spanning-tree detail
```

#### 3. VLAN配置

| 检查项 | 说明 | 优先级 |
|--------|------|--------|
| VLAN一致性 | 与文档一致 | P2 |
| Trunk配置 | 允许VLAN正确 | P2 |
| 接口分配 | 正确分配 | P2 |

**检查方法**:
```bash
# 华为/H3C
display vlan
display port vlan

# 思科
show vlan brief
show interfaces switchport
```

#### 4. MAC地址表

| 检查项 | 正常状态 | 异常情况 | 优先级 |
|--------|----------|----------|--------|
| MAC数量 | 正常范围 | 异常增长 | P2 |
| MAC震荡 | 稳定 | 频繁变化 | P1 |

**检查方法**:
```bash
# 华为/H3C
display mac-address
display mac-address static

# 思科
show mac address-table
show mac address-table count
```

#### 5. ARP表

| 检查项 | 正常状态 | 异常情况 | 优先级 |
|--------|----------|----------|--------|
| ARP条目 | 完整 | 缺失 | P2 |
| ARP冲突 | 无 | 有冲突 | P1 |

**检查方法**:
```bash
# 华为/H3C
display arp

# 思科
show ip arp
show ip arp inspection log
```

---

## 每月巡检

### 目的
全面检查设备配置和长期运行状态。

### 检查项目

#### 1. 配置备份

| 检查项 | 说明 | 优先级 |
|--------|------|--------|
| 配置已备份 | 最新的备份文件 | P1 |
| 配置一致性 | 运行配置=启动配置 | P1 |
| 配置变更记录 | 有变更记录 | P2 |

**检查方法**:
```bash
# 华为/H3C
display current-configuration
display saved-configuration

# 思科
show running-config
show startup-config
```

#### 2. 安全配置

| 检查项 | 检查内容 | 优先级 |
|--------|----------|--------|
| 密码策略 | 复杂度、定期更换 | P1 |
| 远程访问 | SSH已启用，Telnet禁用 | P1 |
| ACL配置 | 最小权限原则 | P1 |
| 登录失败 | 启用登录失败处理 | P2 |
| 空闲超时 | 配置会话超时 | P2 |

**检查方法**:
```bash
# 华为/H3C
display current-configuration | include user
display current-configuration | include ssh
display acl all

# 思科
show running-config | include username
show running-config | include ssh
show access-lists
```

#### 3. 时间和NTP

| 检查项 | 正常状态 | 优先级 |
|--------|----------|--------|
| 系统时间 | 准确 | P1 |
| NTP同步 | 已同步 | P1 |
| 时区配置 | 正确 | P2 |

**检查方法**:
```bash
# 华为/H3C
display clock
display ntp-service status

# 思科
show clock
show ntp status
```

#### 4. SNMP配置

| 检查项 | 检查内容 | 优先级 |
|--------|----------|--------|
| SNMP版本 | 使用v2c或v3 | P1 |
| Community字符串 | 非默认 | P1 |
| ACL限制 | 限制访问源 | P1 |

**检查方法**:
```bash
# 华为/H3C
display snmp-agent community
display snmp-agent target-host

# 思科
show running-config | include snmp
show snmp community
```

#### 5. QoS配置

| 检查项 | 检查内容 | 优先级 |
|--------|----------|--------|
| QoS策略 | 已配置并生效 | P2 |
| 队列配置 | 合理分配 | P2 |
| 流量统计 | 符合预期 | P2 |

**检查方法**:
```bash
# 华为/H3C
display qos policy
display queue-statistics

# 思科
show policy-map
show policy-map interface
```

---

## 季度巡检

### 目的
深度检查和预防性维护。

### 检查项目

#### 1. 固件版本

| 检查项 | 说明 | 优先级 |
|--------|------|--------|
| 版本信息 | 记录当前版本 | P1 |
| 已知问题 | 查询版本Bug | P1 |
| 升级计划 | 评估是否需要升级 | P2 |

**检查方法**:
```bash
display version
show version
```

#### 2. 性能基线

| 检查项 | 说明 | 优先级 |
|--------|------|--------|
| CPU趋势 | 对比历史数据 | P2 |
| 内存趋势 | 对比历史数据 | P2 |
| 流量趋势 | 对比历史数据 | P2 |
| 错误统计 | 分析错误趋势 | P2 |

#### 3. 容量规划

| 检查项 | 说明 | 优先级 |
|--------|------|--------|
| 接口带宽 | 当前使用率vs峰值 | P2 |
| 表项容量 | MAC/ARP/路由表 | P2 |
| 电源冗余 | 冗余配置检查 | P1 |

#### 4. 文档更新

| 检查项 | 说明 | 优先级 |
|--------|------|--------|
| 拓扑图 | 更新网络拓扑 | P2 |
| 配置文档 | 更新配置说明 | P2 |
| IP地址表 | 更新地址分配 | P2 |
| 联系方式 | 更新联系人 | P2 |

#### 5. 灾难恢复

| 检查项 | 说明 | 优先级 |
|--------|------|--------|
| 配置备份 | 验证备份可用 | P1 |
| 恢复流程 | 演练恢复步骤 | P1 |
| 冗余链路 | 测试备份路径 | P1 |

---

## 异常处理流程

### 发现异常后的处理步骤

1. **记录**: 详细记录异常情况
2. **评估**: 判断严重程度和影响范围
3. **上报**: 根据优先级上报
4. **处理**: 采取相应措施
5. **验证**: 确认问题解决
6. **总结**: 更新知识库

### 优先级定义

| 优先级 | 响应时间 | 说明 |
|--------|----------|------|
| P1 | 立即 | 严重影响业务 |
| P2 | 4小时内 | 影响部分功能 |
| P3 | 当天 | 轻微影响 |

---

## 巡检报告模板

### 基本信息

```
设备名称: _______________
设备IP: _______________
巡检日期: _______________
巡检人: _______________
设备型号: _______________
软件版本: _______________
```

### 检查结果

#### 每日检查项

- [ ] 设备状态正常
- [ ] CPU/内存正常
- [ ] 接口状态正常
- [ ] 无严重日志

#### 每周检查项

- [ ] 路由协议正常
- [ ] STP状态稳定
- [ ] VLAN配置正确
- [ ] MAC/ARP正常

#### 每月检查项

- [ ] 配置已备份
- [ ] 安全配置合规
- [ ] 时间/NTP同步
- [ ] SNMP配置正确

#### 季度检查项

- [ ] 版本信息已记录
- [ ] 性能基线已更新
- [ ] 容量规划已评估
- [ ] 文档已更新

### 发现问题

| 序号 | 问题描述 | 优先级 | 处理措施 | 状态 |
|------|----------|--------|----------|------|
| 1 | | | | |
| 2 | | | | |

### 总结和建议

```
_______________
```

---

## 自动化巡检工具

使用本skill提供的健康检查脚本可以自动完成大部分巡检任务：

```bash
# 运行健康检查
python scripts/health_check.py

# 生成巡检报告
python scripts/health_check.py > report.txt

# 批量巡检
python scripts/batch_manager.py
```
