# 通用执行器使用指南

## 🚀 核心优势

通用执行器（`universal_executor.py`）是网络设备自动化的核心工具，**节省大量token**，避免每次生成新脚本。

## 📖 使用方式

### 方式1: 命令行参数（简单任务）

```bash
python scripts/universal_executor.py \
  --host 192.168.56.3 \
  --username admin \
  --password Qch@202503 \
  --device-type H3C \
  --commands "display version" "display vlan" "save force"
```

### 方式2: JSON任务文件（复杂任务）

创建任务文件 `task_vlan_trunk.json`:
```json
{
  "name": "配置VLAN和Trunk",
  "variables": {
    "interface": "GigabitEthernet1/0/1",
    "vlans": "1 100"
  },
  "steps": [
    {
      "name": "创建VLAN",
      "commands": [
        "system-view",
        "vlan 100",
        "quit"
      ],
      "confirm": false
    },
    {
      "name": "配置Trunk接口",
      "commands": [
        "interface {{interface}}",
        "port link-type trunk",
        "port trunk permit vlan {{vlans}}",
        "quit"
      ],
      "confirm": true,
      "rollback": [
        {
          "commands": [
            "interface {{interface}}",
            "undo port link-type",
            "quit"
          ]
        }
      ]
    },
    {
      "name": "保存配置",
      "commands": ["save force"]
    }
  ]
}
```

执行任务:
```bash
python scripts/universal_executor.py \
  --host 192.168.56.3 \
  --username admin \
  --password Qch@202503 \
  --device-type H3C \
  --task task_vlan_trunk.json
```

### 方式3: YAML任务文件

`task_vlan_trunk.yaml`:
```yaml
name: 配置VLAN和Trunk
variables:
  interface: GigabitEthernet1/0/1
  vlans: 1 100

steps:
  - name: 创建VLAN
    commands:
      - system-view
      - vlan 100
      - quit
    confirm: false

  - name: 配置Trunk接口
    commands:
      - interface "{{{interface}}}"
      - port link-type trunk
      - port trunk permit vlan "{{{vlans}}}"
      - quit
    confirm: true
    rollback:
      - commands:
          - interface "{{{interface}}}"
          - undo port link-type
          - quit

  - name: 保存配置
    commands:
      - save force
```

## 💡 高级功能

### 1. 变量替换
使用 `{{{variable}}}` 语法：
```bash
--commands "interface {{{interface}}}" "ip address {{{ip}}} {{{mask}}}"
```

### 2. 条件判断
```json
{
  "condition": {
    "equals": ["{{{device_type}}}", "H3C"]
  },
  "commands": [...]
}
```

### 3. 循环执行
```json
{
  "loop": {
    "items": ["1", "2", "3"],
    "item_var": "vlan_id"
  },
  "commands": ["vlan {{{vlan_id}}}", "quit"]
}
```

### 4. 错误处理
- `stop_on_error`: 遇错停止（默认true）
- `rollback`: 失败时回滚
- `timeout`: 命令超时时间

### 5. 安全确认
- `--confirm`: 执行前确认
- `confirm: true`: 步骤级别确认

## 🎯 实际案例

### 案例1: 查询设备信息
```bash
python scripts/universal_executor.py \
  --host 192.168.56.3 \
  --username admin \
  --password Qch@202503 \
  --device-type H3C \
  --commands "display version" "display vlan" "display interface brief"
```

### 案例2: 配置VLAN
```bash
python scripts/universal_executor.py \
  --host 192.168.56.3 \
  --username admin \
  --password Qch@202503 \
  --device-type H3C \
  --commands "system-view" "vlan 100" "quit" "quit" "save force"
```

### 案例3: 批量配置接口
使用循环功能：
```json
{
  "steps": [{
    "loop": {
      "items": ["GE1/0/1", "GE1/0/2", "GE1/0/3"],
      "item_var": "interface"
    },
    "commands": [
      "interface {{{interface}}}",
      "port link-mode bridge",
      "quit"
    ]
  }]
}
```

## 🔧 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| --host | 设备IP | --host 192.168.56.3 |
| --username | 用户名 | --username admin |
| --password | 密码 | --password xxx |
| --device-type | 设备类型 | --device-type H3C |
| --commands | 命令列表 | --commands "disp ver" "disp vlan" |
| --task | 任务文件 | --task config.json |
| --timeout | 超时时间 | --timeout 60 |
| --confirm | 执行前确认 | --confirm |
| --no-save | 不保存配置 | --no-save |

## ⚡ Token节省对比

### 旧方式（每次生成脚本）
```
用户: 配置vlan100
Claude: 生成configure_vlan.py (500+ tokens)
     运行脚本
     结果反馈
```

### 新方式（使用通用执行器）
```
用户: 配置vlan100
Claude: python universal_executor.py --host xxx --commands "vlan 100" "quit" "save force" (50 tokens)
     结果反馈
```

**节省约90%的token！**

## 📚 经验学习

通用执行器会自动应用经验库中的知识：
- ✅ H3C设备自动使用invoke_shell
- ✅ 自动处理分页
- ✅ 自动处理编码问题
- ✅ save命令自动添加force

经验库位置：`experiences/*.json`

## 🛠️ 故障排除

### 问题1: 连接超时
**解决**: 检查经验001，确认使用invoke_shell模式

### 问题2: 输出被截断
**解决**: 检查经验002，确认自动分页已启用

### 问题3: 保存失败
**解决**: 检查经验004，使用save force命令

## 📝 总结

通用执行器是网络设备自动化的核心工具：
1. **节省token**: 避免重复生成脚本
2. **功能强大**: 支持复杂任务、条件、循环、回滚
3. **自动学习**: 应用经验库避免重复错误
4. **安全可靠**: 支持确认、回滚、错误处理

立即开始使用：`python scripts/universal_executor.py --help`
