"""
美团酒旅 Skill — CLI 包装器

通过 mttravel CLI 调用美团酒旅服务。
CLI 从 ~/.config/meituan-travel/config.json 读取 Token。
"""

import asyncio
import contextlib
import json
import os
from pathlib import Path

from app.config import settings


class MeituanTravel:
    """美团酒旅 Skill 服务"""

    CONFIG_PATH = os.path.expanduser("~/.config/meituan-travel/config.json")

    def sync_config_from_env(self, token: str | None = None) -> bool:
        """
        将项目环境变量中的美团 Token 同步到 mttravel CLI 配置文件。

        Returns:
            True 表示写入了配置文件，False 表示未配置 Token 或配置未变化。
        """
        if token is None:
            token = settings.MEITUAN_TOKEN

        token = token.strip() if token else ""
        if not token:
            return False

        path = Path(self.CONFIG_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)

        cfg: dict = {}
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    cfg = loaded
            except Exception:
                cfg = {}

        if cfg.get("key") == token:
            return False

        cfg["key"] = token
        path.write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        try:
            path.chmod(0o600)
        except OSError:
            pass
        return True

    @property
    def available(self) -> bool:
        if not os.path.exists(self.CONFIG_PATH):
            return False
        try:
            with open(self.CONFIG_PATH) as f:
                cfg = json.load(f)
                return bool(cfg.get("key"))
        except Exception:
            return False

    async def query(
        self,
        city: str,
        query: str,
        timeout: float | None = None,
    ) -> dict:
        """
        调用 mttravel CLI。

        Args:
            city: 目标城市
            query: 自然语言查询（越具体越好）

        Returns:
            {"success": bool, "text": str, "city": str, "query": str}
        """
        if not self.available:
            return {"success": False, "text": "美团 Token 未配置", "error": "no_token"}

        # 查找 mttravel 完整路径（Python 子进程不搜 npm 全局路径）
        import shutil
        cli_path = shutil.which("mttravel") or shutil.which("mttravel.cmd")
        if not cli_path:
            # 尝试常见位置
            import os as _os
            for p in [
                _os.path.expanduser("~/AppData/Roaming/npm/mttravel.cmd"),
                _os.path.expanduser("~/AppData/Roaming/npm/mttravel"),
                "/usr/local/bin/mttravel",
            ]:
                if _os.path.exists(p):
                    cli_path = p
                    break
        if not cli_path:
            return {"success": False, "text": "mttravel CLI 未找到", "error": "cli_not_found"}

        proc = None
        timeout_seconds = settings.MEITUAN_TIMEOUT_SECONDS if timeout is None else timeout
        try:
            proc = await asyncio.create_subprocess_exec(
                cli_path, city, query,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_seconds,
            )

            if proc.returncode != 0:
                err = stderr.decode("utf-8", errors="replace")
                return {"success": False, "text": err, "error": "cli_error"}

            text = stdout.decode("utf-8", errors="replace")

            # 检查 Token 失效
            if any(kw in text for kw in ["鉴权失败", "无效的访问令牌", "Token", "未设置"]):
                return {"success": False, "text": "Token 已失效，请重新创建", "error": "auth_failed"}

            return {"success": True, "text": text, "city": city, "query": query}

        except asyncio.TimeoutError:
            if proc is not None:
                await _terminate_process(proc)
            return {"success": False, "text": "请求超时，请稍后重试", "error": "timeout"}
        except asyncio.CancelledError:
            if proc is not None:
                await _terminate_process(proc)
            raise
        except FileNotFoundError:
            return {"success": False, "text": "mttravel CLI 未安装，请运行: npm i -g @meituan-travel/travel-cli", "error": "cli_not_found"}
        except Exception as e:
            if proc is not None and proc.returncode is None:
                await _terminate_process(proc)
            return {"success": False, "text": f"调用失败: {e}", "error": str(e)}

    async def search_hotels(self, city: str, query: str = "推荐酒店") -> dict:
        """搜索酒店"""
        full_query = f"{query}，返回真实价格和评分"
        return await self.query(city, full_query)

    async def search_attractions(self, city: str, query: str = "推荐景点") -> dict:
        """搜索景点/门票"""
        return await self.query(city, query)

    async def plan_trip(self, city: str, days: int, style: str = "") -> dict:
        """规划行程"""
        q = f"规划{days}天行程"
        if style:
            q += f"，偏好{style}"
        return await self.query(city, q)


meituan = MeituanTravel()


async def _terminate_process(proc, graceful_timeout: float = 3.0) -> None:
    """终止并回收 CLI 子进程。"""
    if proc.returncode is not None:
        await proc.wait()
        return

    with contextlib.suppress(ProcessLookupError):
        proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=graceful_timeout)
    except asyncio.TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        await proc.wait()
