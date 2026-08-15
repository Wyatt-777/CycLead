# CycleLead AI

一个面向自行车配件业务的轻量客户开发自动化项目。

核心目标：

> 自动发现、筛选和整理值得人工开发的潜在客户。

## MVP

第一阶段只做：

```text
发现客户
→ 解析
→ 去重
→ 分类
→ 评分
→ Evidence
→ 人工审核
→ CSV
```

不自动发送消息。

## Codex

打开项目后，请先阅读：

```text
AGENTS.md
```

Codex 应根据其中说明读取 `docs/`。

项目的 MVP 软件开发基线见：[docs/07-software-development-spec.md](docs/07-software-development-spec.md)。

## 开发环境

项目运行时要求 **Python 3.12+**。在具备该版本解释器后，可按以下方式建立本地环境：

```powershell
python3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
pytest
ruff check .
```

初始化本地数据库时，使用版本化迁移：

```powershell
.\.venv\Scripts\alembic.exe upgrade head
```

当前可用的基础命令包括版本命令和健康检查：

```powershell
cyclelead --version
uvicorn app.main:app --reload
```

人工种子发现、解析、去重、分类、评分、资格筛选和人工审核已可用；CSV/JSON 导出仍待实现。

## 人工种子发现

当前唯一实现的来源是本地 JSON 人工种子，不会访问第三方网站。可从
`fixtures/manual_seeds.example.json` 复制格式；每条记录至少提供 `url` 与 `title`，可选字段包括
`snippet`、`country`、`city`、`website`、`social_url`、`email`、`phone` 和 `services`。

先运行迁移，再执行：

```powershell
.\.venv\Scripts\python.exe -m app.cli discover `
  --query "bike custom build" `
  --source manual_seed `
  --input fixtures/manual_seeds.example.json `
  --region Singapore
```

命令输出本次运行的 JSON summary。无效单条记录会计入 `errors` 并继续处理其他记录；无法读取整个输入文件时，运行状态为 `FAILED`。

## 人工审核

查看当前达到阈值、尚未人工审核的线索：

```powershell
.\.venv\Scripts\python.exe -m app.cli review-queue
```

人工记录决定时必须说明理由；每次决定都会保留历史，但不会发送任何消息：

```powershell
.\.venv\Scripts\python.exe -m app.cli review `
  --lead-id <lead-id> `
  --decision ACCEPT `
  --reason "Confirmed workshop with purchasing potential."
```

## 推荐第一条 Codex 指令

```text
请完整阅读 AGENTS.md 和 docs/ 下所有项目文档。

暂时不要写代码。

请先：
1. 总结你对 CycleLead AI 项目的理解；
2. 找出文档中的冲突、遗漏和技术风险；
3. 给出 MVP 实施顺序；
4. 给出第一阶段目录结构；
5. 给出你建议的 Python 依赖；
6. 等我确认后再开始实现。

不得扩大 MVP 范围。
```
