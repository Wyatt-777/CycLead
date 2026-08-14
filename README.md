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
