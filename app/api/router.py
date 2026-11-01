"""
总路由注册 - 汇总所有 API 路由并创建 FastAPI 应用实例
"""

from contextlib import asynccontextmanager
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.auth import router as auth_router
from app.api.v1.chat import router as chat_router
from app.api.v1.data import router as data_router
from app.api.v1.ops import router as ops_router
from app.api.v1.plan import router as plan_router
from app.api.v1.trip import router as trip_router
from app.api.v1.travelogue import router as travelogue_router
from app.api.v1.user import router as user_router
from app.config import settings
from app.exceptions import AppException
from app.schemas.common import ErrorResponse
from app.services.third_party.meituan import meituan
from app.services.vector.vector_store import vector_store


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Initialize process-owned local services and release them on shutdown."""
    try:
        health = vector_store.validate()
        logger.info(
            "[Chroma] status=%s collections=%s path=%s",
            health.status,
            health.collections,
            vector_store.persist_dir,
        )
        meituan.sync_config_from_env()
        Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
        yield
    finally:
        vector_store.close()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS — 允许前端开发服务器直接连接后端（绕过 Vite 代理处理 SSE）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件 — 上传图片
uploads_path = Path(settings.UPLOAD_DIR).resolve()
uploads_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_path)), name="uploads")

# ---- 注册 V1 路由 ----
app.include_router(chat_router, prefix="/api/v1")
app.include_router(plan_router, prefix="/api/v1")
app.include_router(trip_router, prefix="/api/v1")
app.include_router(travelogue_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(data_router, prefix="/api/v1")
app.include_router(ops_router, prefix="/api/v1")


@app.exception_handler(AppException)
async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
    """统一处理应用业务异常"""
    response = ErrorResponse(code=exc.code, message=exc.message)
    return JSONResponse(
        status_code=exc.http_status,
        content=response.model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """统一处理请求参数校验错误"""
    _ = exc
    response = ErrorResponse(code=10001, message="Bad request")
    return JSONResponse(status_code=400, content=response.model_dump())


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """统一处理 FastAPI/Starlette HTTP 异常"""
    code = 10003 if exc.status_code == 404 else 10000 + exc.status_code
    message = "Resource not found" if exc.status_code == 404 else str(exc.detail)
    response = ErrorResponse(code=code, message=message)
    return JSONResponse(status_code=exc.status_code, content=response.model_dump())
