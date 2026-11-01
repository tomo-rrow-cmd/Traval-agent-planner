"""
数据库会话管理
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,      # 使用前检查连接是否有效
    pool_recycle=180,        # 连接最多存活 3 分钟后回收
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
async def close_db():
    """关闭数据库连接"""
    await engine.dispose()
