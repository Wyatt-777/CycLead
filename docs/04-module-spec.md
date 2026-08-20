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

## M06-M08 Phase 1 v1 implementation contract

The following rules make the initial M06-M08 specification deterministic. They do not
change the category caps or score bands defined above.

### Evidence boundary

- A classifier conclusion and every non-zero scoring reason must retain the original
  source URL, the original source text (or the supplied website/social URL itself),
  the candidate capture time, an Evidence type, and confidence.
- A structured email or phone earns contact points only when that exact value appears
  in the source snippet/description or `raw_contact_text`. Missing or unmatched values
  remain stored as supplied but earn no contact score.
- A supplied `/contact` website URL may support the contact-page rule. A supplied
  social URL may support the social rule only after explicit source text classifies the
  candidate as a commercial bicycle business.
- If source text is absent or ambiguous, the classifier returns `UNKNOWN`; it does not
  infer a business type from a name, URL host, city, or contact field.
- `UNRELATED` is used only for an explicit unrelated-business term with no bicycle
  context. Otherwise insufficient evidence remains `UNKNOWN`.

### Classifier precedence

The classifier uses explicit source text, case-insensitively. It recognizes bicycle
context from `bike`, `bicycle`, `自行车`, or `单车`; related Chinese terms included in
the rule list are matched literally. Precedence is:

1. An unrelated business term without bicycle context: `UNRELATED`.
2. A creator signal (`creator`, `influencer`, `youtube`, `channel`, `博主`, `创作者`)
   plus bicycle context and an explicit commercial service: `CONTENT_CREATOR_COMMERCIAL`.
3. An explicit bicycle business phrase: `BIKE_BUILDER`, `BIKE_DISTRIBUTOR`,
   `BIKE_BRAND`, `BIKE_WORKSHOP`, `BIKE_REPAIR`, or `BIKE_SHOP`.
4. A creator signal with bicycle context but no commercial service: `CONTENT_CREATOR_ONLY`.
5. All other cases: `UNKNOWN`.

The explicit English bicycle business phrases are `frame builder`, `bike builder`,
`bike distributor`, `bicycle distributor`, `bicycle wholesale`, `bike brand`,
`bicycle brand`, `bike manufacturer`, `bicycle manufacturer`, `bike workshop`,
`bicycle workshop`, `custom bike build`, `custom bicycle build`, `bike fitting`,
`bike repair`, `bicycle repair`, `bike maintenance`, `bicycle maintenance`,
`bike shop`, `bicycle shop`, `bike store`, and `bicycle store`.

### Deterministic scoring

| Category | Rule | Points | Cap | Evaluation order |
| --- | --- | ---: | ---: | --- |
| Commercial intent | Explicit `custom bike build`, `custom bicycle build`, `bike assembly`, `bicycle assembly`, or `自行车组装` | 20 | 30 | first |
| Commercial intent | Explicit bicycle repair or upgrade phrase | 15 | 30 | second |
| Commercial intent | Explicit bicycle shop, store, or workshop phrase | 15 | 30 | third |
| Product relevance | Each distinct term among `groupset`, `wheelset`, `derailleur`, `crank`, `brake`, `power meter`, `bicycle components` | 5 each | 25 | listed order |
| Contactability | Public email found in original source text | 8 | 20 | first |
| Contactability | Public phone found in original source text | 8 | 20 | second |
| Contactability | Supplied website URL has an explicit contact path | 5 | 20 | third |
| Contactability | Supplied public social URL for an explicitly commercial business | 5 | 20 | fourth |
| Activity | Dated recent-activity claim | 0 in Manual Seed v1 | 10 | not yet implemented |
| Purchase potential | `BIKE_WORKSHOP` or `BIKE_BUILDER` | 15 | 15 | one business-type rule |
| Purchase potential | `BIKE_SHOP`, `BIKE_REPAIR`, or `BIKE_DISTRIBUTOR` | 12 | 15 | one business-type rule |
| Purchase potential | `BIKE_BRAND` | 8 | 15 | one business-type rule |
| Purchase potential | `CONTENT_CREATOR_COMMERCIAL` | 5 | 15 | one business-type rule |

Each capped category is evaluated in the table's stated order. If a rule would exceed
the remaining category cap, it receives only the remaining points and the stored
reason records that actual point value. `CONTENT_CREATOR_ONLY`, `UNRELATED`, and
`UNKNOWN` receive zero purchase-potential points. Each term contributes at most once.
The total remains in the 0-100 range and uses the existing A-D bands.

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

## M09 Phase 1 v1 implementation contract

- `CYCLELEAD_QUALIFICATION_THRESHOLD` is validated as an integer from 0 to 100 and
  defaults to 60. The CLI passes this setting into each discovery run.
- A newly created lead qualifies only when `score >= threshold` and its business type
  is not `UNRELATED`. The threshold comparison is inclusive.
- A qualifying new lead increments `DiscoveryRun.qualified_count`; a newly created lead
  that does not qualify increments `DiscoveryRun.rejected_count`. Confirmed duplicates
  increment only `duplicate_count` and are not counted again as qualified or rejected.
- M09 records review eligibility and a structured qualification log. It does not set a
  human `REJECT` decision or contact anyone. M10 will expose the eligible leads for
  human review and preserve its manual decisions.

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

## M10 Phase 1 v1 implementation contract

- `review-queue` lists leads whose current score meets the configured qualification
  threshold, whose business type is not `UNRELATED`, and whose `review_status` is `NEW`.
  The queue is ordered by descending score, then creation time.
- `review --lead-id <id> --decision <ACCEPT|REJECT|CONTACT_LATER> --reason <text>`
  validates the decision and a nonblank reason before writing data.
- Each decision appends a new `Review` record. `Lead.review_status` shows the latest
  decision for queue display; earlier records are never changed or deleted.
- A missing or currently nonqualified lead is rejected with an explicit error. A lead
  that was previously reviewed may receive a later manual decision, preserving both
  decisions in history.
- Review records are local human judgments only. They do not send messages, change an
  outreach state, or infer new contact information.

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

## M11 Phase 1 v1 implementation contract

- `export --format <csv|json> --output <path>` writes lead records without changing any
  lead, score, evidence, review, or outreach state. The output extension must match the
  requested format.
- The default `accepted` scope exports only leads whose latest human `review_status` is
  `ACCEPT`, so the default file is a human-approved recommended-contact list. Explicit
  `qualified` and `all` scopes are available for review and audit.
- `qualified` applies the current configured score threshold and excludes `UNRELATED`.
  `all` includes every persisted lead. Every record includes the documented CSV fields,
  including the current human review status.
- CSV is UTF-8 with BOM for spreadsheet compatibility and always contains its header.
  JSON is a UTF-8 array. Empty exports produce a header-only CSV or `[]` JSON document.
  In CSV, `score_reason` is a JSON-encoded list; unknown nullable fields remain blank.
- The writer creates the requested parent directory and replaces the destination only
  after a complete temporary file has been written. Filesystem or validation failures
  return a readable error containing the requested destination.

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
