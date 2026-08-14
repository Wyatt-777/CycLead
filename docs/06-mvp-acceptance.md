# CycleLead AI — MVP 验收文档

# 1. 验收目的

避免出现：

> “功能看起来很多，但实际找不到客户。”

MVP 只看真实结果。

---

# 2. P0 验收

## A01 项目可以启动

```bash
pytest
```

必须通过。

---

## A02 可以输入关键词

例如：

```text
自行车组装
bike custom build
bicycle repair shop
```

---

## A03 可以获得候选对象

每条至少包含：

```text
source_url
title/name
captured_at
```

---

## A04 不伪造字段

没有 email：

```text
null
```

---

## A05 去重有效

同 URL 二次执行：

不能新增重复 Lead。

---

## A06 可以评分

输出：

```text
score
band
reasons
```

---

## A07 有证据

A/B 级客户至少存在 1 条核心 Evidence。

---

## A08 可以导出

CSV 可正常打开。

---

## A09 可以统计运行结果

一次任务结束可看到：

```text
discovered
qualified
duplicates
errors
```

---

# 3. Golden Dataset

建立：

```text
fixtures/golden_leads.json
```

包含：

```text
20 positive
20 negative
```

人工标注：

```text
expected_target=true/false
```

每次调整评分器必须重新测试。

---

# 4. 商业验收

技术验收通过后：

连续 7 天运行。

每天：

```text
目标推荐 10~30 条
```

人工记录：

```text
真正值得联系？
YES / NO
```

最终计算：

```text
precision =
YES / total reviewed
```

第一阶段目标：

```text
>= 60%
```

如果低于：

不要继续做 UI / Automation / Agent。

先修：

```text
source quality
parser
classifier
scoring
```

---

# 5. Stop Conditions

出现以下情况时停止扩张：

- 大量错误客户；
- 同一客户重复出现；
- 无法提供评分证据；
- 数据质量不可验证；
- 平台访问方式不稳定；
- 用户根本不愿意联系推荐客户。

项目必须证明“客户真的值得开发”，之后才进入自动化阶段。
