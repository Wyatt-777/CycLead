# CycleLead AI — 系统架构

# 1. MVP 架构

```text
             ┌────────────────┐
             │  Seed / Query  │
             └───────┬────────┘
                     ↓
             ┌────────────────┐
             │ Source Adapter │
             └───────┬────────┘
                     ↓
             ┌────────────────┐
             │ Raw Candidate  │
             └───────┬────────┘
                     ↓
             ┌────────────────┐
             │    Parser      │
             └───────┬────────┘
                     ↓
             ┌────────────────┐
             │  Normalizer    │
             └───────┬────────┘
                     ↓
             ┌────────────────┐
             │ Deduplicator   │
             └───────┬────────┘
                     ↓
             ┌────────────────┐
             │ Lead Scorer    │
             └───────┬────────┘
                     ↓
             ┌────────────────┐
             │ Review Queue   │
             └───────┬────────┘
                     ↓
             ┌────────────────┐
             │ CSV / Report   │
             └────────────────┘
```

---

# 2. 推荐目录

```text
cyclelead-ai/
├── AGENTS.md
├── README.md
├── pyproject.toml
├── .env.example
├── app/
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   │
│   ├── models/
│   │   ├── lead.py
│   │   ├── evidence.py
│   │   └── run.py
│   │
│   ├── sources/
│   │   ├── base.py
│   │   ├── web_search.py
│   │   └── manual_seed.py
│   │
│   ├── pipeline/
│   │   ├── parser.py
│   │   ├── normalizer.py
│   │   ├── deduplicator.py
│   │   ├── scorer.py
│   │   └── qualifier.py
│   │
│   ├── services/
│   │   ├── discovery.py
│   │   ├── lead_service.py
│   │   └── report_service.py
│   │
│   └── exporters/
│       ├── csv_exporter.py
│       └── json_exporter.py
│
├── data/
│   ├── cyclelead.db
│   └── exports/
│
├── fixtures/
│   └── golden_leads.json
│
├── tests/
│   ├── unit/
│   └── integration/
│
└── docs/
    ├── 01-project-plan.md
    ├── 02-development-rules.md
    ├── 03-system-architecture.md
    ├── 04-module-spec.md
    ├── 05-data-model.md
    └── 06-mvp-acceptance.md
```

---

# 3. 为什么选择 Python

此项目主要是：

- 数据采集；
- 文本处理；
- 浏览器自动化；
- AI 调用；
- 数据分析；
- 快速迭代。

因此 MVP 使用 Python 比 Java 更轻。

这并不代表 Java 不合适。
如果未来需要：
- 长期服务；
- 更复杂业务后台；
- 团队协作；
- 企业部署；

可以再考虑 Spring Boot。

---

# 4. 数据流

```text
DiscoveryRun
↓
RawCandidate[]
↓
ParsedCandidate[]
↓
NormalizedLead[]
↓
DeduplicatedLead[]
↓
ScoredLead[]
↓
ReviewQueue
```

任何阶段失败：

不得让整批任务崩溃。

单条失败：

```text
record error
continue next item
```

---

# 5. Source Adapter

统一接口概念：

```python
class LeadSource:
    def discover(self, query) -> list[RawCandidate]:
        ...
```

不同平台通过 adapter 接入。

这样未来增加：

```text
Google
Bing
Douyin
TikTok
Instagram
Maps
Industry Directory
```

不会改动核心 pipeline。

---

# 6. AI 使用原则

LLM 可以用于：

- 判断业务类型；
- 提取描述中的服务；
- 判断是否属于目标客户；
- 解释评分；
- 二次研究摘要。

LLM 不应负责：

- 去重主键；
- URL normalization；
- 电话格式化；
- email 格式校验；
- 确定性字符串解析。

能用规则解决的，不交给模型。

---

# 7. 数据库

MVP：

```text
SQLite
```

理由：
- 零部署；
- 单人使用；
- 数据量低；
- 方便备份。

未来数据规模明显增加后再迁移 PostgreSQL。

---

# 8. 任务执行

第一阶段：

```bash
python -m app.cli discover --query "bike workshop"
```

后续：

```text
Codex Automation
→ 调用脚本
→ 输出 summary
```

Automation 本身不包含业务逻辑。
业务逻辑始终保留在项目代码里。

---

# 9. 可观察性

每次任务产生：

```text
run_id
started_at
finished_at
source
query
discovered
qualified
duplicates
errors
```

这样可以判断系统是不是越来越准确。
