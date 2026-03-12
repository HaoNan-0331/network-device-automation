# 网络设备巡检报告

**报告日期**: {{TIMESTAMP}}
**巡检人员**: {{INSPECTOR}}
**设备数量**: {{DEVICE_COUNT}}
**报告类型**: {{REPORT_TYPE}}

---

## 执行摘要

本次巡检共检查 **{{DEVICE_COUNT}}** 台网络设备，发现 **{{ISSUE_COUNT}}** 个问题。

### 健康评分分布

| 等级 | 设备数量 | 百分比 |
|------|----------|--------|
| 优秀 (90-100分) | {{EXCELLENT_COUNT}} | {{EXCELLENT_PERCENT}}% |
| 良好 (70-89分) | {{GOOD_COUNT}} | {{GOOD_PERCENT}}% |
| 警告 (50-69分) | {{WARNING_COUNT}} | {{WARNING_PERCENT}}% |
| 严重 (<50分) | {{CRITICAL_COUNT}} | {{CRITICAL_PERCENT}}% |

---

## 设备详情

### 1. {{DEVICE_1_NAME}}

**IP地址**: {{DEVICE_1_IP}}
**设备类型**: {{DEVICE_1_TYPE}}
**健康评分**: {{DEVICE_1_SCORE}}/100
**状态**: {{DEVICE_1_STATUS}}

#### 系统信息

| 项目 | 值 |
|------|-----|
| 主机名 | {{DEVICE_1_HOSTNAME}} |
| 设备型号 | {{DEVICE_1_MODEL}} |
| 软件版本 | {{DEVICE_1_VERSION}} |
| 运行时间 | {{DEVICE_1_UPTIME}} |

#### 资源使用情况

| 资源 | 使用率 | 状态 |
|------|--------|------|
| CPU | {{DEVICE_1_CPU}}% | {{DEVICE_1_CPU_STATUS}} |
| 内存 | {{DEVICE_1_MEMORY}}% | {{DEVICE_1_MEMORY_STATUS}} |

#### 接口状态

- **接口总数**: {{DEVICE_1_INTERFACE_COUNT}}
- **UP接口**: {{DEVICE_1_INTERFACE_UP}}
- **DOWN接口**: {{DEVICE_1_INTERFACE_DOWN}}

#### 发现的问题

{{#if DEVICE_1_ISSUES}}
{{#each DEVICE_1_ISSUES}}
- [**{{severity}}**] {{category}}: {{message}}
{{/each}}
{{else}}
无异常
{{/if}}

---

### 2. {{DEVICE_2_NAME}}

**IP地址**: {{DEVICE_2_IP}}
**设备类型**: {{DEVICE_2_TYPE}}
**健康评分**: {{DEVICE_2_SCORE}}/100
**状态**: {{DEVICE_2_STATUS}}

#### 系统信息

| 项目 | 值 |
|------|-----|
| 主机名 | {{DEVICE_2_HOSTNAME}} |
| 设备型号 | {{DEVICE_2_MODEL}} |
| 软件版本 | {{DEVICE_2_VERSION}} |
| 运行时间 | {{DEVICE_2_UPTIME}} |

#### 资源使用情况

| 资源 | 使用率 | 状态 |
|------|--------|------|
| CPU | {{DEVICE_2_CPU}}% | {{DEVICE_2_CPU_STATUS}} |
| 内存 | {{DEVICE_2_MEMORY}}% | {{DEVICE_2_MEMORY_STATUS}} |

#### 接口状态

- **接口总数**: {{DEVICE_2_INTERFACE_COUNT}}
- **UP接口**: {{DEVICE_2_INTERFACE_UP}}
- **DOWN接口**: {{DEVICE_2_INTERFACE_DOWN}}

#### 发现的问题

{{#if DEVICE_2_ISSUES}}
{{#each DEVICE_2_ISSUES}}
- [**{{severity}}**] {{category}}: {{message}}
{{/each}}
{{else}}
无异常
{{/if}}

---

## 问题汇总

### 按严重程度分类

#### 严重问题 (Critical)

{{#if CRITICAL_ISSUES}}
{{#each CRITICAL_ISSUES}}
- **{{device}}** - {{category}}: {{message}}
{{/each}}
{{else}}
无严重问题
{{/if}}

#### 警告问题 (Warning)

{{#if WARNING_ISSUES}}
{{#each WARNING_ISSUES}}
- **{{device}}** - {{category}}: {{message}}
{{/each}}
{{else}}
无警告问题
{{/if}}

#### 一般问题 (Info)

{{#if INFO_ISSUES}}
{{#each INFO_ISSUES}}
- **{{device}}** - {{category}}: {{message}}
{{/each}}
{{else}}
无一般问题
{{/if}}

---

## 趋势分析

### CPU使用率趋势

```
{{CPU_TREND_GRAPH}}
```

### 内存使用率趋势

```
{{MEMORY_TREND_GRAPH}}
```

---

## 建议和行动计划

### 立即处理 (P1)

{{#if P1_ACTIONS}}
{{#each P1_ACTIONS}}
- {{index}}. {{action}} (设备: {{device}})
{{/each}}
{{else}}
无P1级别问题
{{/if}}

### 尽快处理 (P2)

{{#if P2_ACTIONS}}
{{#each P2_ACTIONS}}
- {{index}}. {{action}} (设备: {{device}})
{{/each}}
{{else}}
无P2级别问题
{{/if}}

### 计划处理 (P3)

{{#if P3_ACTIONS}}
{{#each P3_ACTIONS}}
- {{index}}. {{action}} (设备: {{device}})
{{/each}}
{{else}}
无P3级别问题
{{/if}}

---

## 附录

### A. 巡检命令列表

本次巡检执行的命令包括：

```
- display version / show version
- display cpu-usage / show processes cpu
- display memory-usage / show memory statistics
- display interface brief / show ip interface brief
- display logbuffer / show logging
```

### B. 配置备份情况

| 设备 | 备份状态 | 备份文件 | 备份时间 |
|------|----------|----------|----------|
| {{DEVICE_1_NAME}} | {{BACKUP_1_STATUS}} | {{BACKUP_1_FILE}} | {{BACKUP_1_TIME}} |
| {{DEVICE_2_NAME}} | {{BACKUP_2_STATUS}} | {{BACKUP_2_FILE}} | {{BACKUP_2_TIME}} |

### C. 下次巡检计划

- **计划日期**: {{NEXT_INSPECTION_DATE}}
- **重点检查项**: {{NEXT_INSPECTION_FOCUS}}

---

**报告生成时间**: {{GENERATION_TIME}}
**报告生成工具**: 网络设备自动化巡检系统
**联系方式**: {{CONTACT_INFO}}

---

## 使用说明

本报告模板支持以下变量替换：

### 全局变量
- `{{TIMESTAMP}}`: 当前时间戳
- `{{INSPECTOR}}`: 巡检人员
- `{{DEVICE_COUNT}}`: 设备总数
- `{{REPORT_TYPE}}`: 报告类型
- `{{ISSUE_COUNT}}`: 问题总数

### 统计变量
- `{{EXCELLENT_COUNT}}`: 优秀设备数
- `{{GOOD_COUNT}}`: 良好设备数
- `{{WARNING_COUNT}}`: 警告设备数
- `{{CRITICAL_COUNT}}`: 严重设备数
- `{{*_PERCENT}}`: 对应百分比

### 设备变量
- `{{DEVICE_N_NAME}}`: 设备名称
- `{{DEVICE_N_IP}}`: 设备IP
- `{{DEVICE_N_TYPE}}`: 设备类型
- `{{DEVICE_N_SCORE}}`: 健康评分
- `{{DEVICE_N_STATUS}}`: 设备状态
- `{{DEVICE_N_*}}`: 其他设备信息

### 问题变量
- `{{CRITICAL_ISSUES}}`: 严重问题列表
- `{{WARNING_ISSUES}}`: 警告问题列表
- `{{INFO_ISSUES}}`: 一般问题列表

### 模板语法
- `{{#if CONDITION}}...{{/if}}`: 条件渲染
- `{{#each ARRAY}}...{{/each}}`: 循环渲染

使用本模板时，可以用Python的`str.format()`或模板引擎（如Jinja2）进行变量替换。
