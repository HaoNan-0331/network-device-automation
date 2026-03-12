# 网络设备厂商命令对照表

本文档提供华为、H3C、思科、锐捷等主流厂商的常用命令对照。

## 目录

- [系统信息](#系统信息)
- [配置管理](#配置管理)
- [接口管理](#接口管理)
- [路由管理](#路由管理)
- [VLAN管理](#vlan管理)
- [安全相关](#安全相关)
- [监控和诊断](#监控和诊断)

---

## 系统信息

### 查看版本信息

| 厂商 | 命令 |
|------|------|
| 华为 | `display version` |
| H3C | `display version` |
| 思科 (IOS) | `show version` |
| 思科 (NX-OS) | `show version` |
| 锐捷 | `show version` |

### 查看系统时间

| 厂商 | 命令 |
|------|------|
| 华为 | `display clock` |
| H3C | `display clock` |
| 思科 (IOS) | `show clock` |
| 思科 (NX-OS) | `show clock` |
| 锐捷 | `show clock` |

### 查看启动配置

| 厂商 | 命令 |
|------|------|
| 华为 | `display saved-configuration` |
| H3C | `display saved-configuration` |
| 思科 (IOS) | `show startup-config` |
| 思科 (NX-OS) | `show startup-config` |
| 锐捷 | `show startup-config` |

### 查看运行配置

| 厂商 | 命令 |
|------|------|
| 华为 | `display current-configuration` |
| H3C | `display current-configuration` |
| 思科 (IOS) | `show running-config` |
| 思科 (NX-OS) | `show running-config` |
| 锐捷 | `show running-config` |

---

## 配置管理

### 保存配置

| 厂商 | 命令 |
|------|------|
| 华为 | `save` 或 `quit` 后保存 |
| H3C | `save` |
| 思科 (IOS) | `write memory` 或 `copy running-config startup-config` |
| 思科 (NX-OS) | `copy running-config startup-config` |
| 锐捷 | `write` 或 `copy running-config startup-config` |

### 进入配置模式

| 厂商 | 命令 |
|------|------|
| 华为 | `system-view` |
| H3C | `system-view` |
| 思科 (IOS) | `configure terminal` |
| 思科 (NX-OS) | `configure terminal` |
| 锐捷 | `configure terminal` |

### 退出配置模式

| 厂商 | 命令 |
|------|------|
| 华为 | `return` 或 `quit` |
| H3C | `return` 或 `quit` |
| 思科 (IOS) | `end` 或 `exit` |
| 思科 (NX-OS) | `end` 或 `exit` |
| 锐捷 | `end` 或 `exit` |

---

## 接口管理

### 查看所有接口状态

| 厂商 | 命令 |
|------|------|
| 华为 | `display interface brief` |
| H3C | `display interface brief` |
| 思科 (IOS) | `show ip interface brief` |
| 思科 (NX-OS) | `show interface brief` |
| 锐捷 | `show interface status` |

### 查看接口详细信息

| 厂商 | 命令 |
|------|------|
| 华为 | `display interface <interface-name>` |
| H3C | `display interface <interface-name>` |
| 思科 (IOS) | `show interface <interface-name>` |
| 思科 (NX-OS) | `show interface <interface-name>` |
| 锐捷 | `show interface <interface-name>` |

### 配置接口IP地址

| 厂商 | 命令 |
|------|------|
| 华为 | `interface <interface-name>`<br>`ip address <ip> <mask>` |
| H3C | `interface <interface-name>`<br>`ip address <ip> <mask>` |
| 思科 (IOS) | `interface <interface-name>`<br>`ip address <ip> <mask>` |
| 思科 (NX-OS) | `interface <interface-name>`<br>`ip address <ip> <mask>` |
| 锐捷 | `interface <interface-name>`<br>`ip address <ip> <mask>` |

### 启用/关闭接口

| 厂商 | 启用 | 关闭 |
|------|------|------|
| 华为 | `undo shutdown` | `shutdown` |
| H3C | `undo shutdown` | `shutdown` |
| 思科 (IOS) | `no shutdown` | `shutdown` |
| 思科 (NX-OS) | `no shutdown` | `shutdown` |
| 锐捷 | `no shutdown` | `shutdown` |

---

## 路由管理

### 查看路由表

| 厂商 | 命令 |
|------|------|
| 华为 | `display ip routing-table` |
| H3C | `display ip routing-table` |
| 思科 (IOS) | `show ip route` |
| 思科 (NX-OS) | `show ip route` |
| 锐捷 | `show ip route` |

### 查看ARP表

| 厂商 | 命令 |
|------|------|
| 华为 | `display arp` |
| H3C | `display arp` |
| 思科 (IOS) | `show ip arp` 或 `show arp` |
| 思科 (NX-OS) | `show ip arp` |
| 锐捷 | `show arp` |

### 配置静态路由

| 厂商 | 命令 |
|------|------|
| 华为 | `ip route-static <destination> <mask> <next-hop>` |
| H3C | `ip route-static <destination> <mask> <next-hop>` |
| 思科 (IOS) | `ip route <destination> <mask> <next-hop>` |
| 思科 (NX-OS) | `ip route <destination> <mask> <next-hop>` |
| 锐捷 | `ip route <destination> <mask> <next-hop>` |

### 查看OSPF状态

| 厂商 | 命令 |
|------|------|
| 华为 | `display ospf peer` |
| H3C | `display ospf peer` |
| 思科 (IOS) | `show ip ospf neighbor` |
| 思科 (NX-OS) | `show ip ospf neighbor` |
| 锐捷 | `show ip ospf neighbor` |

---

## VLAN管理

### 查看VLAN

| 厂商 | 命令 |
|------|------|
| 华为 | `display vlan` |
| H3C | `display vlan` |
| 思科 (IOS) | `show vlan brief` |
| 思科 (NX-OS) | `show vlan` |
| 锐捷 | `show vlan` |

### 创建VLAN

| 厂商 | 命令 |
|------|------|
| 华为 | `vlan <vlan-id>` |
| H3C | `vlan <vlan-id>` |
| 思科 (IOS) | `vlan <vlan-id>` |
| 思科 (NX-OS) | `vlan <vlan-id>` |
| 锐捷 | `vlan <vlan-id>` |

### 配置接口为Trunk

| 厂商 | 命令 |
|------|------|
| 华为 | `port link-type trunk`<br>`port trunk allow-pass vlan <vlan-list>` |
| H3C | `port link-type trunk`<br>`port trunk permit vlan <vlan-list>` |
| 思科 (IOS) | `switchport trunk encapsulation dot1q`<br>`switchport mode trunk`<br>`switchport trunk allowed vlan <vlan-list>` |
| 思科 (NX-OS) | `switchport mode trunk`<br>`switchport trunk allowed vlan <vlan-list>` |
| 锐捷 | `switchport mode trunk`<br>`switchport trunk allowed vlan <vlan-list>` |

### 配置接口为Access

| 厂商 | 命令 |
|------|------|
| 华为 | `port link-type access`<br>`port default vlan <vlan-id>` |
| H3C | `port link-type access`<br>`port access vlan <vlan-id>` |
| 思科 (IOS) | `switchport mode access`<br>`switchport access vlan <vlan-id>` |
| 思科 (NX-OS) | `switchport mode access`<br>`switchport access vlan <vlan-id>` |
| 锐捷 | `switchport mode access`<br>`switchport access vlan <vlan-id>` |

---

## 安全相关

### 查看ACL

| 厂商 | 命令 |
|------|------|
| 华为 | `display acl all` |
| H3C | `display acl all` |
| 思科 (IOS) | `show access-lists` |
| 思科 (NX-OS) | `show access-lists` |
| 锐捷 | `show access-lists` |

### 查看当前登录用户

| 厂商 | 命令 |
|------|------|
| 华为 | `display users` |
| H3C | `display users` |
| 思科 (IOS) | `show users` |
| 思科 (NX-OS) | `show users` |
| 锐捷 | `show users` |

---

## 监控和诊断

### 查看CPU使用率

| 厂商 | 命令 |
|------|------|
| 华为 | `display cpu-usage` |
| H3C | `display cpu-usage` |
| 思科 (IOS) | `show processes cpu` |
| 思科 (NX-OS) | `show processes cpu` |
| 锐捷 | `show cpu` |

### 查看内存使用率

| 厂商 | 命令 |
|------|------|
| 华为 | `display memory-usage` |
| H3C | `display memory` |
| 思科 (IOS) | `show memory statistics` |
| 思科 (NX-OS) | `show system resources` |
| 锐捷 | `show memory` |

### 查看系统日志

| 厂商 | 命令 |
|------|------|
| 华为 | `display logbuffer` |
| H3C | `display logbuffer` |
| 思科 (IOS) | `show logging` |
| 思科 (NX-OS) | `show logging last 100` |
| 锐捷 | `show logging` |

### 查看MAC地址表

| 厂商 | 命令 |
|------|------|
| 华为 | `display mac-address` |
| H3C | `display mac-address` |
| 思科 (IOS) | `show mac address-table` |
| 思科 (NX-OS) | `show mac address-table` |
| 锐捷 | `show mac-address-table` |

### Ping测试

| 厂商 | 命令 |
|------|------|
| 华为 | `ping <ip-address>` |
| H3C | `ping <ip-address>` |
| 思科 (IOS) | `ping <ip-address>` |
| 思科 (NX-OS) | `ping <ip-address>` |
| 锐捷 | `ping <ip-address>` |

### Traceroute

| 厂商 | 命令 |
|------|------|
| 华为 | `tracert <ip-address>` |
| H3C | `tracert <ip-address>` |
| 思科 (IOS) | `traceroute <ip-address>` |
| 思科 (NX-OS) | `traceroute <ip-address>` |
| 锐捷 | `traceroute <ip-address>` |

---

## 注意事项

1. **权限**: 某些命令需要特权模式或管理员权限
2. **版本差异**: 同一厂商不同版本设备的命令可能略有差异
3. **缩写**: 大多数命令支持缩写（如 `show int` 代表 `show interface`）
4. **上下文帮助**: 使用 `?` 可以获得命令帮助
5. **Tab补全**: 大多数现代设备支持Tab键命令补全

## 快速参考

### 思科IOS模式切换

```
用户模式 (Router>)  →  enable  →  特权模式 (Router#)
特权模式 (Router#)  →  configure terminal  →  全局配置模式 (Router(config)#)
全局配置  →  interface <int>  →  接口配置模式 (Router(config-if)#)
```

### 华为/H3C模式切换

```
用户视图 (<>)  →  system-view  →  系统视图 ([])
系统视图  →  interface <int>  →  接口视图 ([interface])
```
