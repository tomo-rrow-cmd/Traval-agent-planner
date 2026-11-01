# CI/CD 运行说明

本仓库当前使用 GitLab CI，流水线入口为仓库根目录 `.gitlab-ci.yml`。

## 默认 Runner

现阶段流水线适配 GitLab shell runner，而不是 Docker executor。Runner 需要满足：

- executor 为 `shell`。
- tag 包含 `shell`。
- runner 所在机器已经存在 `ai-travel-planning` conda 环境（用于 Python compile/pytest 任务）。
- runner 所在机器需要 Node.js 18+（用于前端 lint、typecheck、test、build 任务），推荐通过 nvm 安装。
- user-mode runner 需要手动保持 `gitlab-runner run` 运行。

注册示例：

```bash
gitlab-runner register \
  --url http://csgitlab.whu.edu.cn \
  --token <runner-token> \
  --name tby-shell \
  --executor shell \
  --tag-list shell
```

验证本机环境：

```bash
gitlab-runner list
conda run -n ai-travel-planning python --version
```

## 默认测试策略

默认 CI 只跑离线门禁，覆盖率不低于 84%：

```bash
python -m pytest -m "not integration" tests --cov=app --cov-fail-under=84
```

离线测试不得依赖真实 PostgreSQL/Redis、第三方 API、LLM API Key、向量库数据、POI 拉取或真实 Agent 编排。API/SSE 契约测试使用本地 stub 或 monkeypatch 验证响应形态。

需要真实外部资源的测试必须标记：

```python
@pytest.mark.integration
```

集成测试只在准备好数据库、Redis、第三方 Key、向量库数据和网络条件后显式运行：

```bash
python -m pytest -m integration tests
```

## 流水线任务

当前流水线分为四个阶段：**validate → test → build → deploy**。

### validate — 快速门禁

- `compile`：Python 语法编译检查（`compileall`），覆盖 `app tests scripts main.py`。
- `frontend:lint`：ESLint 静态检查，`--max-warnings 0`（警告视为错误）。
- `frontend:typecheck`：`vue-tsc -b` 项目引用模式 TypeScript 类型检查。

### test — 离线单元测试

- `pytest`：离线 pytest 门禁（`-m "not integration"`），覆盖率不低于 84%（`--cov=app --cov-fail-under=84`），产出 `coverage.xml` 和 `coverage-html/`。
- `frontend:test`：Vitest 单元测试（`happy-dom` 环境），覆盖组件和 store。

### build — 构建产物

- `frontend:build`：`vue-tsc -b && vite build`，产出 `frontend/dist/`，保留 7 天。
- `docker_image`：手动镜像构建任务（仅 `dev` 分支和 tag）。本机没有可用 Docker daemon 时跳过。

### deploy — 部署

- `deploy_staging`：手动占位任务，真实部署前需要补齐服务器、镜像仓库、运行时密钥和回滚策略。

### 前端 CI 环境要求

前端任务使用 shell runner，需要 Node.js 18+。runner 主机需安装 Node.js，推荐通过 nvm 管理版本：

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash
nvm install 20
nvm use 20
```

前端依赖使用 `npm ci` 安装，依赖缓存基于 `frontend/package-lock.json`。

shell runner 会在仓库目录下生成 `builds/`、`cache/` 等本地产物；这些目录已加入 `.gitignore` 和 `pytest.ini` 的排除范围，不应提交。
