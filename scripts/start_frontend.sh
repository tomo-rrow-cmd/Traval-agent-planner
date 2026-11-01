#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

NO_OPEN=0
PORT_OVERRIDE=""

usage() {
  cat <<'EOF'
用法:
  ./scripts/start_frontend.sh [选项]

常用:
  ./scripts/start_frontend.sh
  ./scripts/start_frontend.sh --port 3000

选项:
  --port PORT      指定 Vite 端口（默认 5173）
  --no-open        启动后不自动打开浏览器
  -h, --help       显示帮助
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      PORT_OVERRIDE="${2:-}"
      if [[ -z "$PORT_OVERRIDE" ]]; then
        echo "错误：--port 需要端口号"
        exit 1
      fi
      shift 2
      ;;
    --no-open)
      NO_OPEN=1
      shift
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

# ---- 环境检查 ----

if ! command -v node >/dev/null 2>&1; then
  echo "错误：未找到 Node.js。请先安装 Node.js 18+。"
  echo "推荐：https://nodejs.org 或 nvm install 18"
  exit 1
fi

NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]')"
if [[ "$NODE_MAJOR" -lt 18 ]]; then
  echo "错误：Node.js 版本过低 (v$(node -v))，需要 18+。"
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "错误：未找到 npm。"
  exit 1
fi

cd "$FRONTEND_DIR"

if [[ ! -d node_modules ]]; then
  echo "首次运行，安装前端依赖…"
  npm install
fi

# ---- 启动 ----

echo "=================================================="
echo "AI Travel Planner - 前端启动"
echo "=================================================="
echo "目录：$FRONTEND_DIR"
echo "Node：$(node -v)"
echo "npm ：$(npm -v)"

VITE_PORT="${PORT_OVERRIDE:-5173}"

echo
echo "Vite 开发服务器 → http://localhost:${VITE_PORT}"
echo "API 代理 → http://localhost:8000"
echo

if [[ "$NO_OPEN" -eq 0 ]]; then
  # 后台自动打开浏览器（fork 避免阻塞 vite）
  (
    sleep 1.5
    if command -v xdg-open >/dev/null 2>&1; then
      xdg-open "http://localhost:${VITE_PORT}" &>/dev/null
    elif command -v open >/dev/null 2>&1; then
      open "http://localhost:${VITE_PORT}" &>/dev/null
    fi
  ) &
fi

if [[ -n "$PORT_OVERRIDE" ]]; then
  exec npx vite --port "$PORT_OVERRIDE"
else
  exec npx vite
fi
