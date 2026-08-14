# CycleLead AI — 开发守则

# 1. 总则

Codex 开发本项目时必须遵循：

**先正确，再自动；先验证，再扩展；先证据，再结论。**

---

# 2. 禁止“张嘴就来”

任何无法确认的信息：

```text
email
phone
location
follower_count
business_type
price
brand
service
```

均不得猜测。

正确：

```json
{
  "email": null,
  "email_status": "not_found"
}
```

错误：

```json
{
  "email": "probably xxx@gmail.com"
}
```

---

# 3. 所有 Lead 必须保留 Evidence

例如：

```json
{
  "claim": "提供自行车组装服务",
  "source_url": "...",
  "source_text": "提供整车组装、升级服务",
  "captured_at": "..."
}
```

如果没有 Evidence：

该字段不得用于高置信度评分。

---

# 4. 抓取规则

优先级：

1. 官方 API
2. 公共页面结构化数据
3. HTML
4. Browser automation
5. Computer Use

Computer Use 不应成为第一选择。

禁止：
- CAPTCHA 绕过；
- 登录限制绕过；
- 指纹伪装；
- 大规模代理池；
- 隐藏自动化特征以规避封禁。

---

# 5. 数据质量规则

## Null > 错误数据

宁可：

```text
phone = null
```

也不要存错号码。

## Raw Data 保留

解析前内容建议保留：

```text
raw_title
raw_description
raw_url
raw_contact_text
```

用于后续定位解析错误。

---

# 6. 去重规则

去重优先级：

1. canonical_url
2. platform + platform_account_id
3. normalized_phone
4. normalized_email
5. normalized_business_name + city

不能只根据显示名称去重。

---

# 7. 评分规则修改

任何评分算法变化：

必须同时：
- 修改代码；
- 修改 `docs/04-module-spec.md`；
- 添加测试；
- 使用 golden dataset 回归。

不允许 Codex 自己“觉得这样更好”就修改权重。

---

# 8. 测试规则

必须存在：

```text
unit tests
integration tests
golden dataset regression
```

至少覆盖：

- 正常页面；
- 缺字段；
- 错误格式；
- 重复；
- 超时；
- 无结果；
- 网络失败。

---

# 9. 日志规则

日志不得只写：

```text
failed
```

应该写：

```text
source=web_search
url=...
stage=parse_contact
error=missing_expected_node
```

---

# 10. 每次 Codex 修改后的报告格式

Codex 完成任务后输出：

```text
## Changed
- ...

## Tests
- command:
- result:

## Behavior
- ...

## Known limitations
- ...

## Next suggested task
- ...
```

禁止只回复：

```text
完成了。
```

---

# 11. 数据库迁移

修改表结构时：

- 必须说明原因；
- 不得删除历史数据；
- 需要 migration；
- 测试旧数据兼容性。

---

# 12. UI 原则

如果做 UI：

优先信息密度和审阅速度。

不要：
- 花哨动画；
- 复杂渐变；
- 无必要 Dashboard；
- 为设计而设计。

核心页面只有：

```text
Lead List
Lead Detail
Run History
Settings
```

---

# 13. 安全边界

任何“发送消息”的能力必须单独立项。

默认：

```text
AUTO_OUTREACH=false
```

不得由 Codex 擅自改为 true。

---

# 14. Definition of Done

每个模块完成必须满足：

- 输入明确；
- 输出明确；
- 异常明确；
- test pass；
- log 可追踪；
- 文档同步；
- 可复现。
