#!/usr/bin/env python3
"""AI Travel Planner 一键启动脚本。

流程：补全 .env -> 校验数据库/第三方 Key（可用则跳过询问）-> 安装依赖
-> 执行数据库迁移 -> 启动后端与前端。

用法：
    python scripts/quickstart.py
    python scripts/quickstart.py --force        # 强制重新校验并询问所有参数
    python scripts/quickstart.py --no-frontend  # 只启动后端
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"

PLACEHOLDER_MARKERS = (
    "your_",
    "your-",
    "change-me",
    "changeme",
    "user:password",
    "sk-xxx",
    "ep-xxx",
)

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
RESET = "\033[0m"


def info(message: str) -> None:
    print(f"{CYAN}[quickstart]{RESET} {message}")


def warn(message: str) -> None:
    print(f"{YELLOW}[quickstart]{RESET} {message}")


def fail(message: str) -> None:
    print(f"{RED}[quickstart]{RESET} {message}")


def ask(prompt: str, default: str = "", secret: bool = False) -> str:
    suffix = f" [{default}]" if default else ""
    while True:
        if secret:
            value = getpass.getpass(f"  {prompt}{suffix}: ")
        else:
            value = input(f"  {prompt}{suffix}: ")
        value = value.strip()
        if value:
            return value
        if default:
            return default
        print(f"  {YELLOW}该项不能为空{RESET}")


def confirm(prompt: str, default_yes: bool = True, auto_yes: bool = False) -> bool:
    if auto_yes:
        return True
    hint = "[Y/n]" if default_yes else "[y/N]"
    answer = input(f"  {prompt} {hint}: ").strip().lower()
    if not answer:
        return default_yes
    return answer in {"y", "yes", "是"}


# ---------------------------------------------------------------- .env


def read_env() -> dict[str, str]:
    data: dict[str, str] = {}
    if not ENV_PATH.exists():
        return data
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def write_env_value(key: str, value: str) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines() if ENV_PATH.exists() else []
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=")
    for index, line in enumerate(lines):
        if pattern.match(line):
            lines[index] = f"{key}={value}"
            break
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(f"{key}={value}")
    ENV_PATH.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def is_placeholder(value: str | None) -> bool:
    if not value:
        return True
    lowered = value.strip().strip('"').strip("'").lower()
    if not lowered:
        return True
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def ensure_env_file() -> None:
    if ENV_PATH.exists():
        return
    if not ENV_EXAMPLE.exists():
        fail("找不到 .env.example，无法生成 .env")
        sys.exit(1)
    ENV_PATH.write_text(ENV_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    info("已从 .env.example 生成 .env")


# ------------------------------------------------------------- 网络校验


def http_json(url: str, headers: dict[str, str] | None = None, timeout: int = 10) -> tuple[int, dict | None]:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.status, json.loads(response.read().decode("utf-8") or "{}")


def validate_deepseek(key: str, base_url: str) -> tuple[bool | None, str]:
    url = f"{(base_url or 'https://api.deepseek.com').rstrip('/')}/models"
    try:
        status, _ = http_json(url, {"Authorization": f"Bearer {key}"})
        return status == 200, f"HTTP {status}"
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return False, f"Key 无效（HTTP {exc.code}）"
        return None, f"HTTP {exc.code}"
    except Exception as exc:  # 网络不可达时无法判断 Key 本身
        return None, str(exc)


def validate_amap(key: str) -> tuple[bool | None, str]:
    query = urllib.parse.urlencode({"address": "北京", "key": key})
    try:
        _, payload = http_json(f"https://restapi.amap.com/v3/geocode/geo?{query}")
        if payload and payload.get("status") == "1":
            return True, "可用"
        reason = (payload or {}).get("info") or "未知错误"
        return False, str(reason)
    except Exception as exc:
        return None, str(exc)


def configure_key(
    env: dict[str, str],
    key: str,
    label: str,
    validator,
    *,
    force: bool,
    required: bool,
    default_hint: str = "",
) -> str | None:
    current = env.get(key, "").strip()
    if current and not is_placeholder(current) and not force:
        valid, reason = validator(current)
        if valid is True:
            print(f"  {GREEN}✓{RESET} {label} 已配置且校验通过，跳过")
            return current
        if valid is None:
            warn(f"{label} 无法在线校验（{reason}），沿用现有值")
            return current
        warn(f"{label} 校验失败：{reason}")

    if not required and not confirm(f"是否配置 {label}？", default_yes=False):
        return env.get(key)

    for _ in range(3):
        hint = f"（{default_hint}）" if default_hint else ""
        value = ask(f"请输入 {label}{hint}")
        valid, reason = validator(value)
        if valid is True:
            write_env_value(key, value)
            env[key] = value
            print(f"  {GREEN}✓{RESET} {label} 校验通过")
            return value
        if valid is None:
            warn(f"无法在线校验（{reason}）")
            if confirm("仍然保存该值？"):
                write_env_value(key, value)
                env[key] = value
                return value
            continue
        fail(f"{label} 校验失败：{reason}")

    if required:
        fail(f"{label} 未配置，无法继续")
        sys.exit(1)
    return env.get(key)


# ---------------------------------------------------------------- 数据库


def split_db_url(url: str) -> dict[str, str]:
    parsed = urllib.parse.urlsplit(url.replace("postgresql+asyncpg://", "postgresql://", 1))
    return {
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
        "user": urllib.parse.unquote(parsed.username or "postgres"),
        "password": urllib.parse.unquote(parsed.password or ""),
        "dbname": (parsed.path or "/travel_planner").lstrip("/") or "travel_planner",
    }


def build_db_url(host: str, port: str, user: str, password: str, dbname: str) -> str:
    auth = urllib.parse.quote(user, safe="")
    if password:
        auth += ":" + urllib.parse.quote(password, safe="")
    return f"postgresql+asyncpg://{auth}@{host}:{port}/{dbname}"


async def _check_database(host: str, port: str, user: str, password: str, dbname: str) -> None:
    import asyncpg

    conn = await asyncpg.connect(
        host=host,
        port=int(port),
        user=user,
        password=password or None,
        database=dbname,
        timeout=5,
    )
    try:
        await conn.execute("SELECT 1")
    finally:
        await conn.close()


async def ensure_database(host: str, port: str, user: str, password: str, dbname: str) -> None:
    import asyncpg

    try:
        await _check_database(host, port, user, password, dbname)
        return
    except asyncpg.InvalidCatalogNameError:
        pass

    conn = await asyncpg.connect(
        host=host,
        port=int(port),
        user=user,
        password=password or None,
        database="postgres",
        timeout=5,
    )
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", dbname)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{dbname}"')
            info(f"已创建数据库 {dbname}")
    finally:
        await conn.close()


def configure_database(env: dict[str, str], force: bool, auto_yes: bool) -> str:
    url = env.get("DATABASE_URL", "").strip()

    if url and not is_placeholder(url) and not force:
        parts = split_db_url(url)
        try:
            asyncio.run(_check_database(**parts))
            print(f"  {GREEN}✓{RESET} 数据库连接正常（{parts['host']}:{parts['port']}/{parts['dbname']}），跳过配置")
            return url
        except ModuleNotFoundError:
            warn("尚未安装 asyncpg，跳过数据库预检，稍后由迁移步骤验证")
            return url
        except Exception as exc:
            if exc.__class__.__name__ == "InvalidCatalogNameError":
                try:
                    asyncio.run(ensure_database(**parts))
                    info(f"数据库 {parts['dbname']} 不存在，已自动创建")
                    return url
                except Exception as create_exc:
                    warn(f"自动创建数据库失败：{create_exc}")
            warn(f"数据库连接失败：{exc}")

    defaults = split_db_url(url) if url else {
        "host": "localhost",
        "port": "5432",
        "user": "postgres",
        "password": "",
        "dbname": "travel_planner",
    }

    for _ in range(3):
        print("  请填写 PostgreSQL 连接信息：")
        host = ask("主机", defaults["host"])
        port = ask("端口", defaults["port"])
        user = ask("用户名", defaults["user"])
        password = getpass.getpass(f"  密码（{defaults['password'] and '已保存，直接回车沿用' or '无密码直接回车'}）: ")
        password = password or defaults["password"]
        dbname = ask("数据库名", defaults["dbname"])

        try:
            asyncio.run(ensure_database(host, port, user, password, dbname))
        except ModuleNotFoundError:
            fail("缺少 asyncpg，请先安装依赖（去掉 --no-install 重试）")
            sys.exit(1)
        except Exception as exc:
            fail(f"连接失败：{exc}")
            if not confirm("重试？", auto_yes=False):
                break
            continue

        new_url = build_db_url(host, port, user, password, dbname)
        write_env_value("DATABASE_URL", new_url)
        env["DATABASE_URL"] = new_url
        print(f"  {GREEN}✓{RESET} 数据库可用，已写入 .env")
        return new_url

    fail("数据库未配置成功，无法继续")
    sys.exit(1)


# ---------------------------------------------------------------- 依赖


def python_dependencies_ready() -> bool:
    required = ("fastapi", "uvicorn", "asyncpg", "sqlalchemy", "alembic", "pydantic_settings")
    import importlib.util

    return all(importlib.util.find_spec(name) is not None for name in required)


def install_python_dependencies(auto_yes: bool) -> None:
    info("安装 Python 依赖（首次可能需要数分钟）")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(ROOT / "requirements.txt")], cwd=ROOT, check=True)


def check_node(auto_yes: bool, no_frontend: bool) -> str | None:
    if no_frontend:
        return None
    npm = shutil.which("npm")
    node = shutil.which("node")
    if not npm or not node:
        warn("未找到 Node.js/npm，跳过前端启动")
        return None

    raw = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
    match = re.match(r"v(\d+)\.(\d+)", raw)
    if match:
        major, minor = int(match.group(1)), int(match.group(2))
        if (major, minor) < (20, 19):
            warn(f"Node {raw} 低于 Vite 8 要求的 20.19，前端可能启动失败")

    if not (ROOT / "frontend" / "node_modules").exists():
        if confirm("安装前端依赖（npm ci）？", auto_yes=auto_yes):
            subprocess.run([npm, "ci"], cwd=ROOT / "frontend", check=True)
        else:
            warn("未安装前端依赖，跳过前端启动")
            return None
    return npm


def run_migrations() -> None:
    info("执行数据库迁移")
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, check=True)


# ---------------------------------------------------------------- 服务


def pump_output(process: subprocess.Popen, prefix: str) -> None:
    stream = process.stdout
    if stream is None:
        return
    for line in iter(stream.readline, ""):
        print(f"{prefix} {line.rstrip()}")
    stream.close()


def spawn(command: list[str], cwd: Path, prefix: str) -> subprocess.Popen:
    kwargs: dict = {
        "cwd": str(cwd),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    process = subprocess.Popen(command, **kwargs)
    threading.Thread(target=pump_output, args=(process, prefix), daemon=True).start()
    return process


def stop_process(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )
        else:
            os.killpg(os.getpgid(process.pid), 15)
            process.wait(timeout=5)
    except Exception:
        try:
            process.terminate()
        except Exception:
            pass


def wait_http(url: str, timeout: int = 90) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except Exception:
            time.sleep(1)
    return False


def wait_port(port: int, timeout: int = 90) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(1)
    return False


# ---------------------------------------------------------------- 主流程


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Travel Planner 一键启动")
    parser.add_argument("-y", "--yes", action="store_true", help="自动确认安装类操作")
    parser.add_argument("--force", action="store_true", help="忽略现有配置，强制重新校验并询问")
    parser.add_argument("--no-install", action="store_true", help="不自动安装依赖")
    parser.add_argument("--no-frontend", action="store_true", help="只启动后端")
    parser.add_argument("--no-reload", action="store_true", help="关闭 uvicorn 热重载")
    parser.add_argument("--no-browser", action="store_true", help="启动后不自动打开浏览器")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    os.chdir(ROOT)

    print("=" * 62)
    print("  AI Travel Planner 一键启动")
    print("=" * 62)

    if sys.version_info < (3, 10):
        fail("需要 Python 3.10+（推荐 3.12）")
        return 1

    ensure_env_file()
    env = read_env()

    if is_placeholder(env.get("SECRET_KEY")) or args.force:
        secret = secrets.token_urlsafe(32)
        write_env_value("SECRET_KEY", secret)
        env["SECRET_KEY"] = secret
        info("已生成随机 SECRET_KEY")

    if not python_dependencies_ready():
        if args.no_install:
            fail("缺少 Python 依赖，且使用了 --no-install")
            return 1
        if not confirm("安装 Python 依赖（pip install -r requirements.txt）？", auto_yes=args.yes):
            fail("未安装依赖，无法继续")
            return 1
        try:
            install_python_dependencies(args.yes)
        except subprocess.CalledProcessError:
            fail("依赖安装失败，请检查网络或手动执行 pip install -r requirements.txt")
            return 1
    else:
        print(f"  {GREEN}✓{RESET} Python 依赖已就绪")

    configure_database(env, force=args.force, auto_yes=args.yes)

    base_url = env.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    configure_key(
        env,
        "DEEPSEEK_API_KEY",
        "DeepSeek API Key",
        lambda value: validate_deepseek(value, base_url),
        force=args.force,
        required=True,
        default_hint="https://platform.deepseek.com 获取",
    )
    configure_key(
        env,
        "AMAP_API_KEY",
        "高德 Web 服务 Key",
        validate_amap,
        force=args.force,
        required=True,
        default_hint="后端用于地理编码/POI/天气",
    )

    vite_key = env.get("VITE_AMAP_KEY", "")
    if is_placeholder(vite_key) or args.force:
        warn("高德 JSAPI Key 无法在服务端校验，只能检查是否填写")
        value = ask("请输入高德 JSAPI Key（前端地图渲染，可复用同一个 Key）")
        write_env_value("VITE_AMAP_KEY", value)
        env["VITE_AMAP_KEY"] = value
    else:
        print(f"  {GREEN}✓{RESET} VITE_AMAP_KEY 已填写，跳过")

    if is_placeholder(env.get("VITE_AMAP_SECURITY_CODE")):
        warn("VITE_AMAP_SECURITY_CODE 未配置：高德 JSAPI 2.0 需要安全密钥，地图可能无法加载")

    npm = check_node(args.yes, args.no_frontend)

    try:
        run_migrations()
    except subprocess.CalledProcessError:
        fail("数据库迁移失败，请检查 DATABASE_URL 与 PostgreSQL 服务状态")
        return 1

    reload_flag = [] if args.no_reload else ["--reload"]
    host = env.get("HOST", "0.0.0.0")
    port = env.get("PORT", "8000")
    info(f"启动后端：http://localhost:{port}")
    backend = spawn(
        [sys.executable, "-m", "uvicorn", "app.api.router:app", "--host", host, "--port", port, *reload_flag],
        ROOT,
        f"{CYAN}[backend]{RESET}",
    )

    if not wait_http(f"http://127.0.0.1:{port}/api/v1/health", timeout=90):
        fail("后端健康检查超时，请查看上方日志")
        stop_process(backend)
        return 1
    print(f"  {GREEN}✓{RESET} 后端已就绪")

    frontend = None
    if npm:
        info("启动前端：http://localhost:5173")
        frontend = spawn([npm, "run", "dev"], ROOT / "frontend", f"{CYAN}[frontend]{RESET}")
        if wait_port(5173, timeout=90):
            print(f"  {GREEN}✓{RESET} 前端已就绪")
            if not args.no_browser:
                webbrowser.open("http://localhost:5173")
        else:
            warn("前端启动超时，请查看上方日志")

    print("=" * 62)
    print("  后端文档：http://localhost:8000/docs")
    print("  前端页面：http://localhost:5173")
    print("  按 Ctrl+C 停止所有服务")
    print("=" * 62)

    try:
        while True:
            time.sleep(1)
            if backend.poll() is not None:
                fail("后端进程已退出")
                return 1
            if frontend is not None and frontend.poll() is not None:
                warn("前端进程已退出")
                frontend = None
    except KeyboardInterrupt:
        print("\n正在停止服务...")
    finally:
        stop_process(frontend)
        stop_process(backend)
    return 0


if __name__ == "__main__":
    sys.exit(main())
