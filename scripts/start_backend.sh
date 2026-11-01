#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

INIT_DB=0
REBUILD_VECTORS=0
SKIP_DB_CHECK=0
NO_RELOAD=0
HOST_OVERRIDE=""
PORT_OVERRIDE=""
CONDA_ENV="${BACKEND_CONDA_ENV:-ai-travel-planning}"
PYTHON_OVERRIDE="${BACKEND_PYTHON:-}"

usage() {
  cat <<'EOF'
用法:
  ./scripts/start_backend.sh [选项]

常用:
  ./scripts/start_backend.sh
  ./scripts/start_backend.sh --init-db
  ./scripts/start_backend.sh --rebuild-vectors

选项:
  --init-db             启动前初始化数据库/表结构
  --rebuild-vectors     启动前从 PostgreSQL 重建 Chroma 向量库
  --skip-db-check       跳过 PostgreSQL 连通性检查
  --no-reload           关闭 uvicorn 热重载
  --host HOST           覆盖 .env/settings.HOST
  --port PORT           覆盖 .env/settings.PORT
  --env CONDA_ENV       使用指定 conda 环境，默认 ai-travel-planning
  --python PYTHON       使用指定 Python 解释器，优先级最高
  -h, --help            显示帮助

环境变量:
  BACKEND_CONDA_ENV     默认 conda 环境名
  BACKEND_PYTHON        指定 Python 解释器，等同 --python

Python 选择顺序:
  --python/BACKEND_PYTHON -> 当前 python -> .venv -> conda -> uv -> python/python3
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --init-db)
      INIT_DB=1
      shift
      ;;
    --rebuild-vectors)
      REBUILD_VECTORS=1
      shift
      ;;
    --skip-db-check)
      SKIP_DB_CHECK=1
      shift
      ;;
    --no-reload)
      NO_RELOAD=1
      shift
      ;;
    --host)
      HOST_OVERRIDE="${2:-}"
      if [[ -z "$HOST_OVERRIDE" ]]; then
        echo "错误：--host 需要地址"
        exit 1
      fi
      shift 2
      ;;
    --port)
      PORT_OVERRIDE="${2:-}"
      if [[ -z "$PORT_OVERRIDE" ]]; then
        echo "错误：--port 需要端口"
        exit 1
      fi
      shift 2
      ;;
    --env)
      CONDA_ENV="${2:-}"
      if [[ -z "$CONDA_ENV" ]]; then
        echo "错误：--env 需要 conda 环境名"
        exit 1
      fi
      shift 2
      ;;
    --python)
      PYTHON_OVERRIDE="${2:-}"
      if [[ -z "$PYTHON_OVERRIDE" ]]; then
        echo "错误：--python 需要解释器路径或命令名"
        exit 1
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数：$1"
      usage
      exit 1
      ;;
  esac
done

cd "$PROJECT_ROOT"
export PYTHONPATH="$PROJECT_ROOT${PYTHONPATH:+:$PYTHONPATH}"

PYTHON_CMD=()
PYTHON_SOURCE=""

python_has_core_deps() {
  "$@" - <<'PY' >/dev/null 2>&1
import importlib.util

missing = [
    module
    for module in ("uvicorn", "fastapi", "sqlalchemy", "asyncpg")
    if importlib.util.find_spec(module) is None
]
raise SystemExit(1 if missing else 0)
PY
}

conda_python_available() {
  [[ -n "$CONDA_ENV" ]] || return 1
  command -v conda >/dev/null 2>&1 || return 1
  conda run --no-capture-output -n "$CONDA_ENV" python -c "import sys" >/dev/null 2>&1
}

uv_supports_requirements() {
  command -v uv >/dev/null 2>&1 || return 1
  [[ "$(uv run --help 2>/dev/null)" == *"--with-requirements"* ]]
}

select_python_cmd() {
  if [[ -n "$PYTHON_OVERRIDE" ]]; then
    PYTHON_CMD=("$PYTHON_OVERRIDE")
    PYTHON_SOURCE="指定 Python"
    return
  fi

  if command -v python >/dev/null 2>&1 && python_has_core_deps python; then
    PYTHON_CMD=(python)
    PYTHON_SOURCE="当前 python"
    return
  fi

  if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]] && python_has_core_deps "$PROJECT_ROOT/.venv/bin/python"; then
    PYTHON_CMD=("$PROJECT_ROOT/.venv/bin/python")
    PYTHON_SOURCE=".venv"
    return
  fi

  if conda_python_available; then
    PYTHON_CMD=(conda run --no-capture-output -n "$CONDA_ENV" python)
    PYTHON_SOURCE="conda:$CONDA_ENV"
    return
  fi

  if command -v uv >/dev/null 2>&1; then
    if [[ -f requirements.txt ]] && uv_supports_requirements; then
      PYTHON_CMD=(uv run --with-requirements requirements.txt python)
      PYTHON_SOURCE="uv + requirements.txt"
    else
      PYTHON_CMD=(uv run python)
      PYTHON_SOURCE="uv"
    fi
    return
  fi

  if command -v python >/dev/null 2>&1; then
    PYTHON_CMD=(python)
    PYTHON_SOURCE="系统 python"
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD=(python3)
    PYTHON_SOURCE="系统 python3"
    return
  fi

  echo "错误：未找到可用的 python、python3、conda 或 uv。"
  echo "请先安装 Python 3.12+，或安装 uv/conda 后重试。"
  exit 1
}

select_python_cmd

run_python() {
  "${PYTHON_CMD[@]}" "$@"
}

echo "=================================================="
echo "AI Travel Planner - 后端启动"
echo "=================================================="
echo "项目目录：$PROJECT_ROOT"
echo "Python：${PYTHON_CMD[*]}"
echo "来源：$PYTHON_SOURCE"

if [[ ! -f .env ]]; then
  echo "提示：未找到 .env，将使用代码默认配置。通常首次运行需要先：cp .env.example .env"
fi

run_python - <<'PY'
import importlib.util
import sys

missing = [
    module
    for module in ("uvicorn", "fastapi", "sqlalchemy", "asyncpg")
    if importlib.util.find_spec(module) is None
]
if missing:
    print("缺少 Python 依赖：" + ", ".join(missing))
    print("请先安装依赖：pip install -r requirements.txt")
    sys.exit(1)
PY

SETTINGS_OUTPUT="$(run_python - <<'PY'
from app.config import settings

print(settings.HOST)
print(settings.PORT)
print("1" if settings.DEBUG else "0")
print(settings.LOG_LEVEL.lower())
PY
)"
mapfile -t SETTINGS <<< "$SETTINGS_OUTPUT"

APP_HOST="${HOST_OVERRIDE:-${SETTINGS[0]}}"
APP_PORT="${PORT_OVERRIDE:-${SETTINGS[1]}}"
APP_DEBUG="${SETTINGS[2]}"
APP_LOG_LEVEL="${SETTINGS[3]}"

if command -v ss >/dev/null 2>&1; then
  if ss -ltn | awk '{print $4}' | grep -Eq "[:.]${APP_PORT}$"; then
    echo
    echo "错误：端口 $APP_PORT 已被占用。请先停止旧后端，或用 --port 指定其他端口。"
    exit 1
  fi
fi

if [[ "$INIT_DB" -eq 1 ]]; then
  if ! command -v psql >/dev/null 2>&1 || ! command -v createdb >/dev/null 2>&1; then
    echo "错误：--init-db 需要 PostgreSQL 客户端命令 psql 和 createdb。"
    exit 1
  fi
  echo
  echo "[1/4] 初始化数据库"
  run_python scripts/init_db.py
else
  echo
  echo "[1/4] 跳过数据库初始化（需要时加 --init-db）"
fi

if [[ "$SKIP_DB_CHECK" -eq 0 ]]; then
  echo
  echo "[2/4] 检查 PostgreSQL 连接"
  run_python - <<'PY'
import asyncio
import sys

from app.db.session import engine


async def main() -> None:
    try:
        async with engine.connect() as conn:
            await conn.exec_driver_sql("SELECT 1")
    except Exception as exc:
        print("PostgreSQL 连接失败。请检查 .env 里的 DATABASE_URL 和本机 PostgreSQL 服务。")
        print(f"错误信息：{exc}")
        print("首次运行可尝试：./scripts/start_backend.sh --init-db")
        sys.exit(1)
    finally:
        await engine.dispose()


asyncio.run(main())
PY
else
  echo
  echo "[2/4] 跳过 PostgreSQL 连接检查"
fi

if [[ "$REBUILD_VECTORS" -eq 1 ]]; then
  echo
  echo "[3/4] 重建 Chroma 向量库"
  run_python scripts/rebuild_vectors.py
else
  echo
  echo "[3/4] 跳过向量库重建（需要时加 --rebuild-vectors）"
fi

echo
echo "[4/4] 启动 uvicorn"
if [[ "$APP_DEBUG" == "1" ]]; then
  echo "地址：http://localhost:${APP_PORT}/docs"
else
  echo "地址：http://localhost:${APP_PORT}"
fi

UVICORN_ARGS=(app.api.router:app --host "$APP_HOST" --port "$APP_PORT" --log-level "$APP_LOG_LEVEL")
if [[ "$NO_RELOAD" -eq 0 && "$APP_DEBUG" == "1" ]]; then
  UVICORN_ARGS+=(--reload)
fi

exec "${PYTHON_CMD[@]}" -m uvicorn "${UVICORN_ARGS[@]}"
