# 质量、安全与演进边界

本文件记录 CI/CD、测试、安全和架构演进边界。

## 1. CI/CD 与测试边界

当前 GitLab CI 以稳定离线门禁为默认目标：

- `.gitlab-ci.yml` 适配带 `shell` tag 的 GitLab shell runner。
- runner 所在机器需要有 `ai-travel-planning` conda 环境。
- 默认 pytest 命令为 `python -m pytest -m "not integration" tests`。
- 真实 PostgreSQL/Redis、第三方 API、LLM API Key、向量库数据、POI 拉取和真实 Agent 编排测试必须标记 `@pytest.mark.integration`，默认 CI 跳过。
- API/SSE 契约测试使用 stub 或 monkeypatch 验证 wire shape，不触发真实外部依赖。
- shell runner 产生的 `builds/`、`cache/` 目录不得提交，也不得被 pytest 收集。

## 2. 安全边界

- 认证默认使用 JWT：Access Token 短有效期，Refresh Token 较长有效期。
- 权限模型使用 RBAC：普通用户、运营人员、管理员。
- 普通用户只能访问自己的数据；任何跨用户访问必须显式鉴权。
- 密码使用 bcrypt 或 Argon2，不存储明文。
- 传输层使用 HTTPS；敏感字段存储加密或脱敏。
- 所有外部输入必须校验类型、长度、格式、范围。
- 日志、错误响应、导出文件不得泄露敏感信息。

## 3. 可演进约束

V1.0 不上来就拆微服务，但必须保留可拆分条件：

- 模块按业务领域组织。
- 跨模块调用通过接口或服务方法完成。
- 第三方服务通过适配器隔离。
- 数据模型保持清晰归属，不共享随意拼装的全局状态。
- 新增 Agent 通过注册机制接入，不修改中央协调器核心流程。

V2.0 可优先拆分的服务：

- 用户服务
- 方案服务
- 订单服务
- 支付服务
- 预订服务
- 智能体服务
- 消息服务
- 内容/搜索服务
