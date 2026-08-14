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

```text
leads.canonical_url UNIQUE where possible
email nullable
phone nullable
score 0..100
```

删除 lead 时不要级联删除原始 run 数据，除非明确设计。
