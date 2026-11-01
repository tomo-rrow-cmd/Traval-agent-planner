# 工程实现边界

本目录记录工程实现边界，用于约束 V1.0/V2.0 范围、模块边界、Agent 编排、API、数据、质量、安全和演进策略。

## 阅读顺序

1. [产品、模块与 Agent 边界](01-boundaries.md)
2. [数据、API 与第三方集成边界](02-data-and-integrations.md)
3. [质量、安全与演进边界](03-quality-and-evolution.md)

## 维护说明

- 本目录记录工程实现口径；架构决策以 `.agent/decisions.md` 的显式决策为准。
- 编码、测试、分支和提交规范以 `.agent/conventions.md` 为准。
- 当前代码结构快照见 [../snapshots/code-structure.md](../snapshots/code-structure.md)。
- 与原始技术架构章节存在口径差异时，优先遵守 `.agent/decisions.md`，再回到对应专题文档补齐说明。
