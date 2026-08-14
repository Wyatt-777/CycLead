# CycleLead AI — 数据模型

# Lead

```json
{
  "id": "uuid",
  "name": "Example Bike Studio",
  "business_type": "BIKE_WORKSHOP",
  "description": "...",
  "country": "SG",
  "city": "Singapore",
  "website": "https://...",
  "social_url": "https://...",
  "email": null,
  "phone": null,
  "source": "web",
  "source_url": "https://...",
  "score": 82,
  "score_band": "A",
  "score_reason": [
    "Provides custom bike builds",
    "Publishes component upgrade work",
    "Public business contact available"
  ],
  "review_status": "NEW",
  "created_at": "...",
  "updated_at": "..."
}
```

---

# Evidence

```json
{
  "id": "uuid",
  "lead_id": "uuid",
  "evidence_type": "SERVICE_CLAIM",
  "field": "services",
  "value": "custom bike build",
  "source_text": "...",
  "source_url": "...",
  "captured_at": "...",
  "confidence": 0.95
}
```

---

# DiscoveryRun

```json
{
  "id": "uuid",
  "query": "bike custom build",
  "source": "web",
  "status": "SUCCESS",
  "started_at": "...",
  "finished_at": "...",
  "discovered_count": 50,
  "parsed_count": 45,
  "duplicate_count": 8,
  "qualified_count": 15,
  "error_count": 5
}
```

---

# Review

```json
{
  "id": "uuid",
  "lead_id": "uuid",
  "decision": "ACCEPT",
  "reason": "Real workshop, component purchasing potential",
  "reviewed_at": "..."
}
```

---

# Suggested SQLite Tables

```text
leads
evidences
discovery_runs
reviews
queries
```

---

# Critical Constraints

## Phase 1 Persistence Contract

为满足可追溯、去重和运行审计要求，Phase 1 的 SQLite 实现补充以下内部字段和表：

- `raw_candidates`：保存 `discovery_run_id`、原始 URL、标题、描述、联系人文本、抓取时间、处理状态和单条错误；它是解析问题的定位依据。
- `leads`：除业务展示字段外，保存 `canonical_url`、平台/平台账号、归一化邮箱、电话和名称。`canonical_url` 可空但在存在时唯一。
- `discovery_runs`：额外保存 `rejected_count`，以支持 M12 的完整运行报告。
- `queries`：保存查询、来源、地区和是否启用，供 Seed Manager 复用。

`raw_candidates.lead_id` 在 Lead 删除时设为 `NULL`，而不是删除原始候选或运行记录；Evidence 和 Review 阻止删除其所属 Lead，以保留证据与人工判断历史。

所有枚举值、分数范围和 Evidence 置信度范围由数据库约束及 Pydantic 输入契约共同校验。输入 URL 只接受绝对 HTTP(S) 地址；此校验不会联网访问或补全 URL。

---

```text
leads.canonical_url UNIQUE where possible
email nullable
phone nullable
score 0..100
```

删除 lead 时不要级联删除原始 run 数据，除非明确设计。
