# 外部服务与数据源决策

> 索引：[.agent/decisions.md](../../.agent/decisions.md) · 范围：D-021 ~ D-026

## D-021：天气适配当前使用高德天气

- 决策：当前天气适配器实际调用高德天气接口并读取 `AMAP_API_KEY`。和风天气/心知天气保留为可替换供应商方向。
- 原因：现有代码已切换到高德天气，协作文档需反映实际实现。
- 影响：真实天气接入须经服务适配器封装，并补充离线 mock 测试。

## D-022：RAG 和第三方查询属于数据源能力，不进入 V1.0 交易闭环

- 决策：Chroma/BGE、美团酒旅 CLI、12306 查询可作为推荐和规划数据源，但 V1.0 不实现真实预订、支付、出票或订单履约。
- 原因：数据查询和交易履约的风险、合规、状态管理完全不同。
- 影响：`services/third_party/` 只能提供查询或推荐输入；下单、支付、退款等必须按 V2.0 能力处理。

## D-023：RAG 和外部数据默认可降级

- 决策：BGE 模型未缓存、Chroma 无数据、Token 缺失、第三方网络失败时，系统应返回可解释降级结果，默认离线测试不得失败。
- 原因：本地开发和 CI 经常没有完整外部资源，契约稳定性应优先于真实数据可用性。
- 影响：依赖外部资源的用例标记 `integration`；普通测试通过 mock/stub/monkeypatch 验证。

## D-024：认证注册路径纳入 API 契约

- 决策：`POST /api/v1/auth/register` 纳入 API 契约和 README 路径概览。
- 原因：源码已提供手机号+密码注册，文档漏列会导致前端和测试误判可用路径。
- 影响：注册、验证码、登录、刷新 Token、登出共同构成认证契约 MVP。

## D-025：RAG 默认采用 BGE-M3 召回加 reranker 重排

- 决策：通过 ModelScope 下载/缓存 `BAAI/bge-m3` 生成 1024 维 embedding，Chroma Top-K 召回后用 `BAAI/bge-reranker-base` 重排。
- 原因：旧 512 维 embedding 与当前推荐质量和重排需求不匹配。
- 影响：切换模型后需重建 `chroma_data/` collection；离线测试通过 monkeypatch 避免依赖真实模型。

## D-026：美团酒旅 Token 从项目环境同步到 mttravel CLI

- 决策：启动时读取 `.env` 中的 `MEITUAN_TOKEN`，同步写入 `~/.config/meituan-travel/config.json`。
- 原因：CLI 读取固定用户级配置，项目级环境变量更便于团队协作和部署注入。
- 影响：不得提交真实 Token；Token 缺失时跳过同步。
