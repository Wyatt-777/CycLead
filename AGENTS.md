# AGENTS.md

## 1. Project Identity
Project name: **CycleLead AI**
Purpose: Build a lightweight customer-development automation system that discovers, evaluates, deduplicates, and organizes potential bicycle-industry customers.

The first business goal is not “full automation”.
The first business goal is:

> Consistently produce a small number of high-quality, human-reviewable sales leads that are worth contacting.

## 2. Current Phase
Current phase: **MVP / Phase 1**

Only implement:
1. Lead source adapters
2. Lead normalization
3. Lead deduplication
4. Lead scoring
5. Evidence capture
6. Review queue
7. Export
8. Run logs

Do NOT implement unless explicitly requested:
- automatic cold messaging
- automatic email sending
- automatic social-media DM
- automatic quotation
- automatic order placement
- CAPTCHA bypass
- login/session circumvention
- anti-bot evasion
- large-scale scraping intended to bypass platform restrictions

## 3. Source of Truth
Before changing code, read the relevant files under `docs/`.

Priority:
1. `AGENTS.md`
2. `docs/01-project-plan.md`
3. `docs/02-development-rules.md`
4. `docs/03-system-architecture.md`
5. `docs/04-module-spec.md`
6. `docs/05-data-model.md`
7. `docs/06-mvp-acceptance.md`

If documents and implementation disagree:
- do not silently choose one;
- explain the conflict;
- prefer the latest explicit requirement;
- update documentation after the implementation decision is confirmed.

## 4. Product Principles
Follow these principles:

### P1. Quality over quantity
30 qualified leads are more useful than 3,000 noisy records.

### P2. Every score must be explainable
Never output only a number.
A lead score must include evidence and reasons.

### P3. Never fabricate missing information
If email, phone, location, follower count, business type, or other fields are unknown:
use `null`, `unknown`, or an explicit missing state.

### P4. Evidence first
Important lead claims should retain:
- source URL
- captured text/snippet
- capture timestamp
- source type

### P5. Human approval before outreach
MVP ends at “recommended contact list”.
Outreach remains manual.

### P6. Idempotent workflow
Running the same input twice should not produce duplicate leads.

### P7. Observable execution
Every run must produce logs and a summary:
- total discovered
- total parsed
- deduplicated
- qualified
- rejected
- errors
- elapsed time

## 5. Engineering Constraints
Prefer a lightweight implementation.

Recommended stack:
- Backend: Python 3.12+
- API: FastAPI
- Database: SQLite for MVP
- ORM: SQLModel or SQLAlchemy
- Browser automation where legitimately required: Playwright
- HTML parsing: BeautifulSoup/lxml
- Validation: Pydantic
- Testing: pytest
- Export: CSV + JSON
- Optional UI later: simple local web dashboard

Do not introduce:
- Kubernetes
- distributed queues
- Redis
- Kafka
- microservices
- vector database
unless a concrete requirement justifies them.

## 6. Development Workflow
For each feature:

1. Read the relevant spec.
2. Inspect existing implementation.
3. State assumptions.
4. Implement the smallest correct change.
5. Add/update tests.
6. Run relevant tests.
7. Update documentation if behavior changed.
8. Report:
   - files changed
   - what changed
   - test result
   - known limitations
   - next recommended task

## 7. Definition of Done
A feature is done only if:
- code is implemented;
- input validation exists;
- failure behavior is defined;
- tests cover the main path;
- logs are usable;
- documentation matches behavior;
- no known data fabrication exists.

## 8. Safety / Compliance Rules
Do not add functionality intended to:
- evade CAPTCHAs;
- rotate identities to evade platform restrictions;
- bypass login/security controls;
- defeat rate limits;
- collect clearly private/non-public personal data;
- spam users automatically.

Prefer public business information and user-authorized sources.

## 9. Codex Working Style
Be conservative.
Do not rewrite unrelated files.
Do not refactor large areas without need.
Do not claim a test passed unless it was actually run.
Do not claim a source field was captured unless it exists in evidence.
Do not “improve” scoring rules without updating the scoring specification.

When uncertain, preserve data and mark uncertainty instead of guessing.
