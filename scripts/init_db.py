"""
数据库初始化脚本 — 建库 + 建表

用法：
    python scripts/init_db.py
"""

import os
import subprocess
import sys
from importlib import import_module
from pathlib import Path
from urllib.parse import unquote, urlsplit

from alembic import command
from alembic.config import Config


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

settings = import_module("app.config").settings


def _database_config() -> dict[str, str | None]:
    parsed = urlsplit(settings.DATABASE_URL)
    name = parsed.path.lstrip("/")
    if not name:
        print("DATABASE_URL 未包含数据库名称，请检查 .env")
        sys.exit(1)

    return {
        "name": name,
        "user": parsed.username or "postgres",
        "password": unquote(parsed.password) if parsed.password else None,
        "host": parsed.hostname or "localhost",
        "port": str(parsed.port or 5432),
    }


def _postgres_env(password: str | None) -> dict[str, str]:
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password
    return env


def validate_database_url() -> None:
    """尽早拦截 .env 中未替换的数据库占位配置。"""
    parsed = urlsplit(settings.DATABASE_URL)
    if parsed.username == "user" and parsed.password == "password":
        print("检测到 .env 中的 DATABASE_URL 仍是默认占位值：")
        print("  postgresql+asyncpg://user:password@localhost:5432/travel_planner")
        print("\n请把它改成你的 PostgreSQL 实际账号，例如：")
        print("  DATABASE_URL=postgresql+asyncpg://postgres:<你的postgres密码>@localhost:5432/travel_planner")
        sys.exit(1)


def create_database():
    """通过 psql 创建数据库（如果不存在）"""
    cfg = _database_config()
    env = _postgres_env(cfg["password"])

    result = subprocess.run(
        [
            "psql",
            "-U", cfg["user"],
            "-h", cfg["host"],
            "-p", cfg["port"],
            "-d", "postgres",
            "-Atc",
            f"SELECT 1 FROM pg_database WHERE datname='{cfg['name']}'",
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        print("检查数据库是否存在失败，请确认 DATABASE_URL 中的 PostgreSQL 账号和密码正确。")
        if result.stderr.strip():
            print(result.stderr.strip())
        sys.exit(1)

    if result.stdout.strip() == "1":
        print(f"数据库 '{cfg['name']}' 已存在，跳过创建")
        return

    created = subprocess.run(
        [
            "createdb",
            "-U", cfg["user"],
            "-h", cfg["host"],
            "-p", cfg["port"],
            cfg["name"],
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    if created.returncode != 0:
        print(f"建库失败：无法创建数据库 '{cfg['name']}'。")
        if created.stderr.strip():
            print(created.stderr.strip())
        sys.exit(1)
    print(f"数据库 '{cfg['name']}' 创建成功")


def apply_migrations() -> None:
    """通过 Alembic 创建并升级数据库结构"""
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    print("数据库迁移完成")


def main():
    print("=" * 50)
    print("AI Travel Planner - 数据库初始化")
    print("=" * 50)

    validate_database_url()
    create_database()
    apply_migrations()

    print("\n初始化完成！")


if __name__ == "__main__":
    main()
