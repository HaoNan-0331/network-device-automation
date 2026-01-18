 network-device-automation-skills介绍

  🎯 技能概述

  network-device-automation 是一个功能强大的网络设备运维自动化技能，支持通过 SSH/Telnet/串口对主流网络设备进行统一管理和自动化操作。

  支持的厂商

  - 华为
  - 华三 (H3C)
  - 思科
  - 锐捷
  - 其他支持标准 CLI 的设备

  ---
  ⭐ 核心功能

  1. 资产台账管理 ⭐️

  这是该技能的核心亮点，可以提前录入设备信息，实现自动化查找和连接：

  # 添加设备
  python scripts/asset_manager.py add

  # 查看所有设备
  python scripts/asset_manager.py list

  # 查找设备（支持IP、名称、ID、模糊搜索）
  python scripts/asset_manager.py find 192.168.1.1

  台账数据结构：
  devices:
    core-sw-01:
      name: "核心交换机-01"
      host: "192.168.1.1"
      device_type: "hp_comware"
      username: "admin"
      password: ""  # base64编码，可留空交互式输入
      group: "core"
      tags: ["production"]

  2. 通用执行器 ⭐️

  节省大量 token，无需每次生成新脚本：

  # 方式1: 命令行参数
  python scripts/universal_executor.py \
    --host 192.168.56.3 \
    --username admin \
    --password xxx \
    --device-type H3C \
    --commands "display version" "display vlan"

  # 方式2: JSON/YAML 任务文件（支持变量、循环、回滚）
  python scripts/universal_executor.py --task config.json

  高级功能：
  - 变量替换：{{{variable}}}
  - 条件判断
  - 循环执行
  - 错误回滚
  - 自动应用经验库

  3. 设备连接管理

  # 智能匹配连接（支持IP、名称、ID）
  python scripts/device_connector.py 192.168.1.1
  python scripts/device_connector.py 核心交换机-01

  4. 配置管理

  # 配置备份/恢复/对比
  python scripts/config_backup.py

  5. 健康检查与巡检

  python scripts/health_check.py

  检查项目：
  - CPU/内存使用率
  - 接口状态和流量
  - 路由表完整性
  - ARP/MAC 表
  - 错误日志
  - 冗余协议状态

  6. 批量设备操作

  # 批量配置备份、巡检等
  python scripts/batch_manager.py core

  ---
  📂 文件结构

  network-device-automation/
  ├── SKILL.md                    # 完整技能文档
  ├── QUICK_START.md              # 快速开始指南
  ├── ASSET_LEDGER_GUIDE.md       # 资产台账使用指南
  ├── assets/
  │   ├── inventory.yaml          # 资产台账文件
  │   └── templates/              # 模板文件
  ├── scripts/
  │   ├── universal_executor.py   # 通用执行器（核心）⭐️
  │   ├── device_connector.py     # 设备连接器
  │   ├── asset_manager.py        # 资产管理器
  │   ├── command_executor.py     # 命令执行器
  │   ├── config_backup.py        # 配置备份
  │   ├── health_check.py         # 健康检查
  │   ├── batch_manager.py        # 批量管理
  │   └── h3c_*.py               # H3C专用脚本
  ├── experiences/                # 经验库（避免重复错误）
  │   ├── 001_command_execution.json
  │   ├── 002_pagination.json
  │   └── ...
  └── references/                 # 参考文档
      ├── vendor_commands.md      # 厂商命令对照
      ├── troubleshooting_guide.md
      └── inspection_checklist.md

  ---
  💡 使用场景

  场景1: 日常运维（使用台账）

  # 1. 首次添加设备到台账
  python scripts/asset_manager.py add

  # 2. 之后直接连接，自动查找
  python scripts/device_connector.py 192.168.1.1

  # 3. 执行命令
  python scripts/universal_executor.py --host 192.168.1.1 --commands "display version"

  场景2: 批量巡检

  # 对所有核心设备进行健康检查
  python scripts/batch_manager.py core --health-check

  场景3: 配置变更

  # 使用任务文件进行复杂配置
  python scripts/universal_executor.py --task vlan_config.json --confirm

  场景4: 故障应急

  # 快速连接设备并执行诊断
  python scripts/device_connector.py 核心交换机-01
  python scripts/health_check.py --detailed

  ---
  🔥 核心优势

  1. 资产台账: 一次录入，自动匹配，大幅提升效率
  2. 通用执行器: 节省 ~90% token，避免重复生成脚本
  3. 经验学习: 自动应用经验库，避免重复错误
  4. 跨厂商支持: 统一接口，支持华为/H3C/思科/锐捷
  5. 安全可靠: 支持确认、回滚、错误处理

  ---
  ⚠️ H3C设备特别说明

  基于实测经验，H3C设备（Comware V7）需要注意：
  ┌──────────┬─────────────────────────┐
  │   要点   │          说明           │
  ├──────────┼─────────────────────────┤
  │ 连接方式 │ 必须使用 invoke_shell() │
  ├──────────┼─────────────────────────┤
  │ 分页处理 │ 必须处理 ---- More ---- │
  ├──────────┼─────────────────────────┤
  │ 超时设置 │ 设置 30秒+ 超时         │
  ├──────────┼─────────────────────────┤
  │ 编码处理 │ 使用 errors='ignore'    │
  ├──────────┼─────────────────────────┤
  │ 设备类型 │ 使用 hp_comware         │
  └──────────┴─────────────────────────┘
  ---
  🚀 快速开始

  # 1. 进入技能目录
  cd skills/network-device-automation

  # 2. 添加设备
  python scripts/asset_manager.py add

  # 3. 测试连接
  python scripts/device_connector.py <设备IP或名称>

  # 4. 执行命令
  python scripts/universal_executor.py --host <IP> --commands "display version"

  ---
  📊 Token节省对比
  ┌────────────────────────┬──────────────┐
  │          方式          │  Token消耗   │
  ├────────────────────────┼──────────────┤
  │ 旧方式（每次生成脚本） │ ~500+ tokens │
  ├────────────────────────┼──────────────┤
  │ 新方式（通用执行器）   │ ~50 tokens   │
  ├────────────────────────┼──────────────┤
  │ 节省                   │ ~90%         │
  └────────────────────────┴──────────────┘
  这个技能非常适合日常网络设备运维工作，特别是需要管理大量设备或频繁执行操作的场景！
