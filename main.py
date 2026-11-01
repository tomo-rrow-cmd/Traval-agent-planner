"""
AI Travel Planner - 项目启动入口
一键同时启动前端 (Vite) 和后端 (FastAPI)
"""

import os
import signal
import subprocess
import sys
import threading
import time

import uvicorn
from app.config import settings


PROJECT_DIR = os.path.dirname(__file__)
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")
BACKEND_DIR = os.path.join(PROJECT_DIR, "app")

# 进程引用，用于优雅关闭
_backend_thread: threading.Thread | None = None
_frontend_proc: subprocess.Popen | None = None


def _stream_output(stream, prefix: str, color_code: str):
    """实时打印子进程输出，每条日志加上颜色前缀"""
    reset = "\033[0m"
    for line in iter(stream.readline, ""):
        sys.stdout.write(f"{color_code}[{prefix}]{reset} {line}")
        sys.stdout.flush()
    stream.close()


def start_backend(host: str, port: int, reload: bool, log_level: str):
    """在后端线程中启动 uvicorn"""
    uvicorn.run(
        "app.api.router:app",
        host=host,
        port=port,
        reload=reload,
        reload_dirs=[BACKEND_DIR] if reload else None,
        reload_includes=["*.py"] if reload else None,
        log_level=log_level,
    )


def start_frontend():
    """启动 Vite 前端开发服务器，返回 Popen 对象"""
    try:
        proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=FRONTEND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid,  # 创建独立进程组，方便 kill
        )
    except FileNotFoundError:
        print("[ERROR] 未找到 npm，请确认 Node.js 已安装")
        sys.exit(1)

    # 启动两个线程分别读取 stdout / stderr
    threading.Thread(
        target=_stream_output,
        args=(proc.stdout, "frontend", "\033[36m"),  # 青色
        daemon=True,
    ).start()
    threading.Thread(
        target=_stream_output,
        args=(proc.stderr, "frontend", "\033[36m"),
        daemon=True,
    ).start()

    return proc


def shutdown():
    """优雅关闭前后端"""
    print("\n[shutdown] 正在关闭...")

    if _frontend_proc and _frontend_proc.poll() is None:
        print("[shutdown] 停止前端 dev server...")
        os.killpg(os.getpgid(_frontend_proc.pid), signal.SIGTERM)
        try:
            _frontend_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(_frontend_proc.pid), signal.SIGKILL)
        print("[shutdown] 前端已停止")

    if _backend_thread and _backend_thread.is_alive():
        print("[shutdown] 后端已随主进程退出")

    print("[shutdown] 再见 👋")


def main():
    global _backend_thread, _frontend_proc

    # 注册信号处理
    signal.signal(signal.SIGINT, lambda sig, frame: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(0))

    print("=" * 56)
    print("  ✈️  AI Travel Planner")
    print(f"  后端:  http://{settings.HOST}:{settings.PORT}")
    print(f"  前端:  http://localhost:5173")
    print(f"  API:   http://localhost:{settings.PORT}/docs")
    print("=" * 56)

    # 启动前端
    _frontend_proc = start_frontend()

    # 给 Vite 一点启动时间
    time.sleep(1.5)

    # 启动后端（主线程阻塞在这里）
    _backend_thread = threading.current_thread()
    try:
        start_backend(
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level=settings.LOG_LEVEL.lower(),
        )
    except KeyboardInterrupt:
        pass
    finally:
        shutdown()


if __name__ == "__main__":
    main()
