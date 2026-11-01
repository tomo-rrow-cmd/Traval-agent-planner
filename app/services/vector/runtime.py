"""本地向量模型运行时。"""

import asyncio
import threading
from collections.abc import Callable
from typing import ParamSpec, TypeVar


Params = ParamSpec("Params")
Result = TypeVar("Result")

_model_execution_lock = threading.Lock()


def _run_locked(
    operation: Callable[Params, Result],
    args: tuple,
    kwargs: dict,
) -> Result:
    with _model_execution_lock:
        return operation(*args, **kwargs)


async def run_model_operation(
    operation: Callable[Params, Result],
    *args: Params.args,
    **kwargs: Params.kwargs,
) -> Result:
    """在线程池中串行执行共享的本地模型操作。"""
    return await asyncio.to_thread(_run_locked, operation, args, kwargs)
