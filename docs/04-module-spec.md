# CycleLead AI — 功能模块开发文档

# M01 — Seed Manager

## 目的
管理：
- 搜索关键词；
- 已知目标客户；
- 排除关键词；
- 国家/地区；
- 平台。

## 输入

```json
{
  "query": "bike custom build",
  "region": "Singapore",
  "source": "web"
}
```

## 输出
DiscoveryJob。

---

# M02 — Source Adapter

## 目的
从某个来源获取公开候选对象。

## 输出

```json
{
  "source": "web",
  "url": "...",
  "title": "...",
  "snippet": "...",
  "captured_at": "..."
}
```

必须保存原始 URL。

---

# M03 — Candidate Parser

提取：

```text
name
description
location
website
social_url
phone
email
services
```

规则：

解析失败不得伪造。

---

# M04 — Normalizer

统一：

```text
URL
phone
email
business name
location
platform
```

示例：

```text
HTTP://Example.com/
https://example.com
```

应归一化用于比较。

---

# M05 — Deduplicator

输出：

```text
NEW
DUPLICATE
POSSIBLE_DUPLICATE
```

Possible Duplicate 不得直接删除。

---

# M06 — Lead Classifier

业务类型：

```text
BIKE_WORKSHOP
BIKE_SHOP
BIKE_REPAIR
BIKE_BUILDER
BIKE_DISTRIBUTOR
BIKE_BRAND
CONTENT_CREATOR_COMMERCIAL
CONTENT_CREATOR_ONLY
UNRELATED
UNKNOWN
```

---

# M07 — Lead Scorer

总分：

```text
0-100
```

建议初始规则：

## 商业意图 0-30

```text
明确提供组装服务 +20
维修/升级服务 +15
明确门店/工作室 +15
```

取最高组合但总计不超过 30。

## 产品相关度 0-25

出现：
- groupset
- wheelset
- derailleur
- crank
- brake
- power meter
- bicycle components

越接近主营产品得分越高。

## 联系可能性 0-20

```text
公开 email +8
公开 phone +8
官网联系页 +5
商业社媒 +5
```

封顶 20。

## 活跃度 0-10

近期仍有业务活动证据。

## 采购潜力 0-15

小店/工作室/经销属性明显：
增加评分。

纯个人内容号：
降低。

---

# Score Bands

```text
80-100  A / Strong
60-79   B / Worth Review
40-59   C / Low Priority
0-39    D / Reject
```

---

# M08 — Evidence Engine

每条高分原因必须对应 evidence。

示例：

```json
{
  "type": "SERVICE_CLAIM",
  "text": "Custom bike builds available",
  "url": "...",
  "confidence": 0.94
}
```

---

# M09 — Qualification Engine

满足：

```text
score >= configured_threshold
AND
business_type != UNRELATED
```

才进入 Review Queue。

默认：

```text
threshold = 60
```

---

# M10 — Review Queue

人工动作：

```text
ACCEPT
REJECT
CONTACT_LATER
```

并支持备注。

人工判断必须保留，用于以后改进评分规则。

---

# M11 — Export

CSV 字段至少：

```text
lead_id
name
business_type
score
score_reason
location
website
social_url
email
phone
source_url
status
created_at
```

---

# M12 — Run Reporter

每次执行输出：

```text
Run ID
Query
Source
Start
End
Discovered
Parsed
Duplicates
Qualified
Rejected
Errors
```

---

# M13 — Research Enrichment（Phase 2）

只针对 A/B Lead。

进一步获取：

```text
business summary
main products
brands sold
services
country
public contacts
recommended approach
```

不能对所有候选执行，避免成本失控。

---

# M14 — Outreach（不属于 MVP）

状态：

```text
NOT_IMPLEMENTED
```

未来即便开发，也必须：

```text
human approval required
```
