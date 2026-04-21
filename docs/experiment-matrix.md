# 实验矩阵（Group 259）

## 自变量

| 维度 | 取值 |
|------|------|
| 架构 | EC2（ALB+容器） / Serverless（API Gateway + Lambda 容器） |
| 负载形态 | 冷请求（空闲≥30min 后首包）、突发、阶梯升压、持续平台期（5–10 min） |
| 输入 | `manifest.json` 中 `role`：smoke / baseline / large / stress |
| 并发 | Lambda 默认或预留并发；EC2 单副本或多 worker（若启用需单独说明） |

## 因变量

- 端到端延迟 p50 / p90 / p99（定义见 [metrics-definitions.md](metrics-definitions.md)）
- 错误率与 HTTP 状态分布
- Lambda：`Init Duration`、内存/超时事件
- （可选）粗略 AWS 账单维度

## API Gateway 同步边界（重要）

- 经 **API Gateway → Lambda** 的 **同步** 调用受约 **29s** 限制；超过则不适合作为「端到端成功」路径，除非改为 **异步 job**、Step Functions，或压测 **直连** Lambda Function URL / 内网 ALB（需在报告中声明对比口径）。
- **阶段 1** 实现同步 API；**large / stress** 样例的正式对比在 **阶段 2** 与报告中与上述策略对齐。

## 变更记录

| 日期 | 说明 |
|------|------|
| 2026-04-21 | 初版：与 OpenAPI v1 及 Phase0/1 实施文档对齐。 |
