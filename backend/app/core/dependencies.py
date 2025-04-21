from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from redis.asyncio import Redis as AsyncRedis, ConnectionPool
from app.db.base import Base
from app.core.config import settings
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request

# Database setup
async_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10
)

AsyncSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=async_engine, class_=AsyncSession
)

async def get_async_db():
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()

@asynccontextmanager
async def redis_lifespan(app: FastAPI):
    """
    Context manager for Redis connection pool lifespan.
    Initializes the pool on startup and closes it on shutdown.
    Stores the pool in app.state instead of a global variable.
    """
    print("Initializing Redis connection pool...")
    try:
        redis_pool = ConnectionPool.from_url(settings.REDIS_URL)
        client = AsyncRedis(connection_pool=redis_pool)
        await client.ping()
        app.state.redis_pool = redis_pool
        print("Redis connection pool created and connection successful.")
    except Exception as e:
        print(f"Failed to connect to Redis or create pool: {e}")
        app.state.redis_pool = None

    yield

    if hasattr(app.state, "redis_pool") and app.state.redis_pool:
        print("Closing Redis connection pool...")
        app.state.redis_pool.disconnect()
        print("Redis connection pool closed.")


async def get_redis(request: Request) -> AsyncRedis:
    """
    Dependency that provides an async Redis client using the shared pool.
    Pulls the pool from app.state.
    """
    redis_pool = getattr(request.app.state, "redis_pool", None)
    if redis_pool is None:
        print("ERROR: Redis connection pool is not available.")
        raise HTTPException(status_code=503, detail="Redis service unavailable")

    return AsyncRedis(connection_pool=redis_pool)
