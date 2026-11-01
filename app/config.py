"""
全局配置加载 - 从环境变量读取所有配置项
"""

from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置"""

    # ---- 应用 ----
    APP_NAME: str = "AI Travel Planner"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    SECRET_KEY: str = "change-me-in-production"

    # ---- JWT ----
    JWT_SECRET: str = "change-me-in-production"  # 生产环境务必更换
    JWT_ACCESS_EXPIRE: int = 7200                 # Access Token 有效期 (秒) = 2 小时
    JWT_REFRESH_EXPIRE: int = 604800             # Refresh Token 有效期 (秒) = 7 天

    # ---- 数据库 ----
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/travel_planner"
    TEST_DATABASE_URL: str = ""
    REDIS_URL: str = "redis://localhost:6379/0"

    # ---- LLM 服务 ----
    # 主模型：DeepSeek
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    LLM_REQUEST_TIMEOUT_SECONDS: float = 60.0
    LLM_SDK_MAX_RETRIES: int = 0

    # 备选：豆包
    DOUBAO_API_KEY: str = ""
    DOUBAO_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    DOUBAO_MODEL: str = ""

    # 备选：通义千问
    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    # ---- 地图服务 ----
    AMAP_API_KEY: str = ""

    # ---- 天气服务 ----
    QWEATHER_API_KEY: str = ""

    # ---- 美团酒旅 mttravel CLI ----
    MEITUAN_TOKEN: str = ""
    MEITUAN_TIMEOUT_SECONDS: float = 30.0

    # ---- 文件上传 ----
    UPLOAD_DIR: str = "./uploads"
    UPLOAD_MAX_SIZE_MB: int = 10

    # ---- 文件上传 ----
    UPLOAD_DIR: str = "./uploads"
    UPLOAD_MAX_SIZE_MB: int = 10

    # ---- Embedding / RAG ----
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    CHROMA_LOCK_TIMEOUT_SECONDS: float = 15.0
    EMBEDDING_MODEL_ID: str = "BAAI/bge-m3"
    EMBEDDING_DIM: int = 1024
    EMBEDDING_MODEL_CACHE_DIR: str = "./cache/modelscope"
    EMBEDDING_LOCAL_FILES_ONLY: bool = True
    RAG_TOP_K: int = 40
    RAG_FINAL_K: int = 25
    RERANKER_ENABLED: bool = True
    RERANKER_MODEL_ID: str = "BAAI/bge-reranker-base"
    RERANKER_MODEL_CACHE_DIR: str = "./cache/modelscope"
    RERANKER_LOCAL_FILES_ONLY: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value: Any) -> bool:
        """兼容 dev/release 等环境标识写法"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
