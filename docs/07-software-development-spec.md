# CycleLead AI — MVP 软件开发规格说明书

## 1. 文档目的与适用范围

本文档把现有项目规划、开发守则、架构、模块规格、数据模型和验收要求整理为一套可实施的软件开发基线。它定义 **MVP / Phase 1** 的功能、技术边界、实现顺序、质量要求和验收方式。

本文档适用于 CycleLead AI 的本地单用户 MVP。它不是联网采集平台、CRM 或自动外联系统的设计文档。

### 1.1 项目目标

系统接收关键词或人工种子，从合规的公开业务信息中形成可审核的潜在自行车行业客户线索，并提供：

- 可追溯的来源和证据；
- 可解释的评分与优先级；
- 幂等去重；
- 人工审核队列；
- CSV、JSON 导出和每次运行的统计报告。

MVP 的交付物是“推荐联系名单”，不是自动联系行为。

### 1.2 当前实现状态

当前仓库已完成 Phase 1 数据基础和手工验证闭环：Python 包、依赖清单、最小 FastAPI 健康检查、版本 CLI、Pydantic 输入契约、SQLite ORM 模型、Alembic 迁移、确定性归一化、优先级去重、人工种子来源、结构化候选解析、运行统计、分类、固定规则评分、Evidence 生成与幂等写入、测试框架、配置模板和 golden dataset 标注合同。网页来源适配器、非结构化 HTML 解析、审核服务、导出和真实人工标注的 golden dataset 尚未实现。本文档其余内容描述待实施的目标状态，不表示这些组件已经存在。

### 1.3 M06-M08 implementation status (2026-08-15)

The repository now implements a conservative rule-based classifier, the fixed Phase 1
scorer with category caps and A-D bands, readable score reasons, and evidence persistence
with provenance validation and per-lead idempotence. Manual Seed discovery runs these
stages only for new leads; confirmed duplicates retain their original score and evidence,
while their new raw candidate remains retained for audit.

Manual Seed has no dated activity field, so activity scoring is deliberately zero until a
compliant source adapter supplies a dated public activity claim. The checked-in golden
dataset contract remains empty and pending manual labeling; unit and integration tests
cover the fixed rules, but a true 20-positive/20-negative golden regression cannot run
until human-labeled examples are supplied.

## 2. 需求基线与实施决定

需求优先级为：`AGENTS.md`、`01-project-plan.md`、`02-development-rules.md`、`03-system-architecture.md`、`04-module-spec.md`、`05-data-model.md`、`06-mvp-acceptance.md`。

为消除文档间容易产生误解的地方，本 MVP 采用以下明确决定：

| 事项 | 实施决定 | 依据 |
| --- | --- | --- |
| 审核队列 | 作为 Phase 1 MVP 功能实现 | `AGENTS.md` 将 Review Queue 列为 MVP，模块 M10 已定义行为 |
| 运行入口 | 命令行优先；FastAPI 仅作为本地 API 适配层，不依赖 UI | 架构文档已定义 `python -m app.cli discover` |
| 采集来源 | 先实现人工种子和至多一个稳定、合规的公开网页来源 | 项目规划要求第一版只接入 1–2 个稳定来源 |
| 外联状态 | MVP 只记录审核决定；不实现发送、私信、报价、下单或自动外联 | 项目边界和安全要求 |
| 二次研究与看板 | 均为后续阶段，不纳入本次实现 | M13、项目 Phase 2/3 |

若后续实现需要改变评分权重、数据表或这些决定，必须先更新对应规格、加入迁移及回归测试，再修改代码。

## 3. 项目边界

### 3.1 MVP 范围内

1. 关键词、地区、来源和人工候选的输入管理。
2. 合规来源适配器和原始候选数据保存。
3. 候选解析、字段归一化、确定性去重和可能重复标记。
4. 业务类型分类、评分、评分理由和证据记录。
5. 合格线索进入人工审核队列，并保留审核决定和备注。
6. CSV、JSON 导出。
7. Discovery Run 日志、统计、错误记录与命令行报告。
8. 单用户本地 SQLite 持久化、数据库迁移、测试数据和自动化测试。

### 3.2 明确不在范围内

- 自动或半自动发送邮件、私信、WhatsApp、社媒消息；
- 自动报价、订单、CRM 流程、成交预测；
- CAPTCHA、登录、会话、风控、限流或平台限制的绕过；
- 代理池、伪装指纹、批量大规模抓取；
- 多用户权限、云端部署、SaaS、移动端、复杂 Dashboard；
- 向量数据库、消息队列、微服务、Redis、Kafka、Kubernetes；
- 对所有候选自动进行二次研究或 LLM 推断。

未知数据必须保存为 `null` 或明确的缺失状态；不得猜测邮箱、电话、地址、业务类型或服务内容。

## 4. 功能规格

### 4.1 核心流程

```text
Seed / Query
  -> Source Adapter
  -> Raw Candidate
  -> Parser
  -> Normalizer
  -> Deduplicator
  -> Classifier + Scorer + Evidence
  -> Qualification
  -> Review Queue
  -> Export / Run Report
```

单条候选解析、网络或存储失败时，系统必须记录结构化错误并继续处理下一条；只有无法创建运行记录、无法打开数据库等系统级故障才终止本次运行。

### 4.2 模块清单

| 模块 | MVP 行为 | 输入验证与失败行为 |
| --- | --- | --- |
| M01 Seed Manager | 创建和校验查询、地区、来源及人工种子 | `query` 去除空白后不得为空；不支持的来源返回明确验证错误 |
| M02 Source Adapter | 输出 `source`、原始 URL、标题、摘要、抓取时间 | 保留原始 URL；网络或解析失败写入 run error，不伪造候选 |
| M03 Parser | 尽力提取名称、描述、位置、网站、社媒、公开电话/邮箱、服务 | 缺失字段为 `null`；原始标题、描述、URL 与联系人文本可追溯保存 |
| M04 Normalizer | 归一化 URL、邮箱、电话、名称、地点、平台字段 | 不可验证或不合法格式保留原始文本并标记为未归一化，不生成猜测值 |
| M05 Deduplicator | 返回 `NEW`、`DUPLICATE` 或 `POSSIBLE_DUPLICATE` | 依次比较 canonical URL、平台账号、电话、邮箱、名称+城市；可能重复不能自动删除 |
| M06 Classifier | 产生既定业务类型枚举 | 证据不足使用 `UNKNOWN`；明确无关使用 `UNRELATED` |
| M07 Scorer | 输出 0–100、A–D 分段、理由及对应证据 | 评分理由没有证据时不得计入高置信度得分；总分必须在 0–100 |
| M08 Evidence Engine | 为关键业务主张和高分原因保存 Evidence | 每条证据必须有来源 URL、原文片段、抓取时间、类型和置信度 |
| M09 Qualification | 分数达到配置阈值且类型不是 `UNRELATED` 时入队 | 默认阈值 60；阈值必须在 0–100 |
| M10 Review Queue | 记录 `ACCEPT`、`REJECT`、`CONTACT_LATER` 和人工备注 | Lead 不存在或非法决定必须拒绝；审核历史不可覆盖删除 |
| M11 Export | 导出可打开的 UTF-8 CSV 与 JSON | 导出为空时仍生成带表头的有效文件；失败写明目标路径与原因 |
| M12 Run Reporter | 显示 run ID、查询、来源、开始/结束、发现、解析、重复、合格、拒绝、错误 | 计数来自已持久化运行数据，不从日志文本推测 |

### 4.3 评分合同

初始评分规则严格沿用 `04-module-spec.md`：商业意图最多 30 分、产品相关度最多 25 分、联系可能性最多 20 分、活跃度最多 10 分、采购潜力最多 15 分。分段如下：

| 分数 | 分段 | 含义 |
| --- | --- | --- |
| 80–100 | A | Strong |
| 60–79 | B | Worth Review |
| 40–59 | C | Low Priority |
| 0–39 | D | Reject |

对 A、B 级线索至少要保存一条核心 Evidence。任何调整权重、关键词、上限或分段的变更必须同步修改 `04-module-spec.md`、golden dataset 回归测试和本文件的评分合同。

## 5. 实现架构与目录

采用单体 Python 应用。来源适配器、业务流水线和导出器必须通过明确接口协作，禁止将采集逻辑、评分规则和数据库访问直接耦合在命令行入口中。

```text
cyclelead-ai/
├── app/
│   ├── api/                 # 本地 FastAPI 路由（可选入口）
│   ├── cli.py               # MVP 主入口
│   ├── config.py
│   ├── db.py
│   ├── models/              # ORM 模型、枚举
│   ├── schemas/             # Pydantic 输入/输出契约
│   ├── sources/             # base、manual_seed、首个合规网页来源
│   ├── pipeline/            # parser、normalizer、deduplicator、classifier、scorer、qualifier
│   ├── services/            # discovery、review、report
│   ├── exporters/           # CSV、JSON
│   └── logging.py
├── alembic/                 # 数据库迁移
├── data/                    # 本地数据库和 exports（不提交真实业务数据）
├── fixtures/golden_leads.json
├── tests/unit/
├── tests/integration/
├── docs/
├── pyproject.toml
├── .env.example
└── README.md
```

### 5.1 运行接口

最低支持以下命令合同：

```bash
python -m app.cli discover --query "bike workshop" --source manual_seed
python -m app.cli export --format csv --output data/exports/leads.csv
python -m app.cli report --run-id <run_id>
```

`discover` 可接受可选 `--region`。来源名称、查询和导出格式应通过 Pydantic 或等价的显式校验；CLI 对用户输入错误返回非零状态码与可读错误，不创建伪造的 Lead。

FastAPI 如实施，仅提供本地调用所需的健康检查、运行、线索查询、审核和导出端点；它不应成为实现核心业务逻辑的唯一入口。

## 6. 技术栈与依赖

| 层级 | 选型 | 用途与限制 |
| --- | --- | --- |
| 运行时 | Python 3.12+ | 单体应用和命令行运行时 |
| API | FastAPI + Uvicorn | 本地、薄适配层；没有 UI 依赖 |
| 校验 | Pydantic v2 | CLI/API/服务边界的数据校验 |
| 持久化 | SQLite + SQLAlchemy 2.x + Alembic | 单用户数据库、可迁移 schema、保留历史运行数据 |
| HTTP | HTTPX | 有超时的公开网页请求 |
| HTML 解析 | BeautifulSoup4 + lxml | 公开 HTML 的确定性解析 |
| 归一化 | 标准库 `urllib`、`email`；`phonenumbers` | URL、邮箱、电话的确定性处理 |
| 导出 | Python 标准库 `csv`、`json` | UTF-8 CSV 与 JSON |
| 日志 | Python `logging`（JSON 或键值格式） | 结构化、可追踪的运行与错误日志 |
| 测试 | pytest + pytest-cov | 单元、集成、回归与覆盖率报告 |
| 代码质量 | Ruff | lint 与格式检查 |
| 可选浏览器 | Playwright | 仅在公开 HTML 无法满足、访问被允许时使用；不用于绕过限制 |

外部 API、LLM 和浏览器自动化不是 MVP 的前置依赖。若引入 LLM，它只能辅助分类或摘要，不能替代 URL 去重、邮箱验证、电话规范化等确定性操作，并且不得凭空生成字段。

## 7. 数据与持久化要求

数据库以 `leads`、`evidences`、`discovery_runs`、`reviews`、`queries` 为基础；为支持可追溯解析，增加 `raw_candidates` 表保存采集原文及其所属 run。真实业务数据、数据库文件、导出结果和密钥不得提交到版本库。

必须满足以下约束：

- Lead 使用 UUID；`score` 为 0–100；`email` 与 `phone` 可为空。
- `canonical_url` 在可生成时唯一；数据库唯一约束与服务层检查共同保证相同 URL 的重复运行不会新建 Lead。
- Evidence 关联 Lead，至少保存 `evidence_type`、字段、值、原文、来源 URL、抓取时间和置信度。
- DiscoveryRun 保存开始、结束、状态及 discovered、parsed、duplicate、qualified、error 计数。
- Review 以追加记录方式保留决定、理由和审核时间；删除 Lead 时不得级联删除原始 run 数据。
- 表结构变更必须通过 Alembic migration；迁移不得无说明地删除历史数据，并需有旧数据兼容测试。

## 8. 可观察性、隐私与合规

每次运行必须生成可查询的 run summary，并在日志中记录 `run_id`、`source`、`query`、阶段、URL（适用时）、错误类型和耗时。日志中不得只写“failed”。

只处理公开可访问的企业信息或用户授权来源。不得采集明显私密的个人信息，不得规避网站访问控制、CAPTCHA、登录、风控、指纹或限流。采集器必须设置合理超时；来源条款、robots 规则或访问限制不允许时，应关闭该适配器并记录原因。

## 9. 分阶段实施计划

| 阶段 | 交付内容 | 完成判定 |
| --- | --- | --- |
| 0. 基础工程 | `pyproject.toml`、应用包、配置、测试框架、Ruff、`.env.example` | 空项目可安装；`pytest` 可运行 |
| 1. 数据契约与存储 | Pydantic、ORM、枚举、迁移、run 和 raw candidate 保存 | 可创建数据库并写入/读取示例运行 |
| 2. 核心流水线 | Parser、Normalizer、Deduplicator、Classifier、Scorer、Evidence、Qualifier | 样本可稳定得到可解释结果；重复运行幂等 |
| 3. 来源与运行服务 | Manual Seed + 一个合规来源、错误隔离、结构化日志 | 单条来源失败不会中断批处理 |
| 4. 审核与导出 | 审核记录、CSV/JSON、报告、CLI；可选本地 API | 可审核、导出、回看任意 run |
| 5. 验收 | 40 条 golden dataset、集成测试、文档核对 | 满足第 10 节的所有 P0 验收项 |

## 10. 测试策略与验收标准

### 10.1 测试层级

| 层级 | 必测内容 |
| --- | --- |
| 单元测试 | URL/邮箱/电话归一化、缺失字段、错误格式、分类、评分上限、理由与 Evidence 映射、去重优先级、阈值边界 |
| 集成测试 | 假来源到 SQLite 的完整流水线、重复运行、单条失败继续、审核记录、CSV/JSON 导出、run 统计 |
| Golden regression | `fixtures/golden_leads.json` 中 20 个正样本和 20 个负样本；每条含 `expected_target`，评分变化必须重新运行 |
| 命令行/API 测试 | 参数校验、空结果、错误状态码、导出路径、报告字段和 UTF-8 CSV 可读性 |
| 迁移测试 | 空数据库初始化、迁移到最新版本、旧数据保留与读取 |

最低质量门槛：`pytest` 全部通过；新改动的核心流水线代码应保持不低于 80% 的行覆盖率；Ruff 无阻塞问题。覆盖率不能替代对 golden dataset 和端到端主路径的验证。

### 10.2 P0 验收映射

| 验收编号 | 通过标准 | 验证方式 |
| --- | --- | --- |
| A01 | 项目可启动，`pytest` 全部通过 | 自动化测试命令 |
| A02 | 可输入如“自行车组装”“bike custom build”的关键词 | CLI/API 参数测试 |
| A03 | 每个候选至少有 source URL、名称/标题和 captured_at | 集成测试 + 数据库断言 |
| A04 | 缺失邮箱存为 `null`，不生成猜测地址 | Parser/Schema 单元测试 |
| A05 | 相同 URL 再运行不新增重复 Lead | 两次完整运行的集成测试 |
| A06 | 每条评分含 score、band、reasons | Scorer 单元与 Golden 测试 |
| A07 | A/B Lead 至少一条核心 Evidence | Qualification/Evidence 集成测试 |
| A08 | CSV 含规定列并由标准 CSV 读取器正常读取 | Export 集成测试 |
| A09 | run 结束可见 discovered、qualified、duplicates、errors | Report 集成测试 |

技术验收通过后，进入商业验收：连续 7 天运行，每日推荐 10–30 条，人工标注 YES/NO；`precision = YES / total reviewed` 应达到至少 60%。未达标时只优先改进来源质量、解析、分类和评分，不扩展 UI、自动化或 Agent。

## 11. Definition of Done 与交付清单

任一模块完成前，必须同时满足：

- 输入、输出、枚举与异常行为已定义并已校验；
- 主路径、缺字段、错误格式、重复、超时、无结果、网络失败均有相应测试；
- 日志能定位到 run、来源和流水线阶段；
- 不生成或声称未捕获的数据；
- 评分变化已同步规格和 golden dataset；
- 数据库变化有 migration 和兼容性测试；
- 用户文档、CLI 示例和已实现行为一致；
- 运行 `pytest`、Ruff 和相关验收命令均通过。

每次功能交付报告必须列出：变更文件、行为、实际执行的测试与结果、已知限制、下一项建议工作。未经实际运行，不得声明测试通过。

## 12. 已知风险与控制措施

| 风险 | 控制措施 |
| --- | --- |
| 公开来源质量低或结构变化 | 只接入稳定来源；保留原始数据和 Evidence；单来源失败不阻断运行 |
| 误判客户类型 | 使用 `UNKNOWN`、人工审核、golden dataset 和 7 天 Precision 验证 |
| 重复或合并错误 | 使用分层键；`POSSIBLE_DUPLICATE` 仅供人工复核，不自动删除 |
| 缺少公开联系方式 | 保持 `null`，不得猜测；联系方式不是入库前提 |
| 评分无法解释 | 强制 score reason 与 Evidence 对应；A/B 无证据不得通过验收 |
| 合规风险 | 仅公开/授权数据；不绕过任何访问限制；必要时禁用来源适配器 |
| 范围膨胀 | 以本文件第 3 节为边界；UI、外联、云服务需单独立项 |
