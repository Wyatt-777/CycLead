# Golden Dataset 标注说明

`golden_leads.json` 是评分器回归测试的数据合同，但它当前仍是待人工标注的空数据集。

在实现评分器前，业务负责人必须填入至少 40 条真实、可公开验证的样本：

- 20 条 `expected_target: true` 的理想客户；
- 20 条 `expected_target: false` 的非目标客户；
- 每条都应保存来源 URL、捕获时间、原始文字或 evidence，并说明人工判断依据。

不得把虚构商家、猜测联系方式或未验证的推断当作 Golden Dataset。该数据集用于回归测试，也用于后续 7 天商业验收的质量基线。
