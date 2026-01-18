# 经验学习模块

本模块用于存储和查询网络设备自动化运维的经验教训，避免重复踩坑。

## 经验数据结构

```json
{
  "id": "001",
  "category": "connection|command_execution|encoding|pagination|script_error",
  "title": "简短的问题标题",
  "problem": "详细问题描述",
  "symptoms": ["错误信息1", "错误信息2"],
  "root_cause": "根本原因分析",
  "solution": "解决方案",
  "code_example": "代码示例",
  "device_type": ["H3C", "Cisco", "Huawei"],
  "prevention": "预防措施",
  "script_fix": "脚本需要修改的地方",
  "timestamp": "ISO 8601格式",
  "verified": true/false,
  "tags": ["tag1", "tag2"]
}
```

## 分类说明

- **connection**: SSH/连接相关问题
- **command_execution**: 命令执行相关问题
- **encoding**: 字符编码相关问题
- **pagination**: 分页处理相关问题
- **script_error**: 脚本本身的错误

## 使用方法

### 查询经验

```python
from experience_manager import ExperienceManager

em = ExperienceManager()
related = em.search("H3C timeout")
```

### 添加经验

```python
em.add_experience({
  "category": "connection",
  "problem": "...",
  "solution": "..."
})
```
