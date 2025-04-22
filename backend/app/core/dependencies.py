from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from redis.asyncio import Redis as AsyncRedis, ConnectionPool
from app.db.base import Base, SessionLocal
from app.core.config import settings
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import asyncio

async_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    pool_pre_ping=True,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_recycle=3600  # Recycle connections after an hour
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


# Global variable to hold the connection pool
redis_pool = None


@asynccontextmanager
async def redis_lifespan(app: FastAPI):
    """
    Context manager for Redis connection pool lifespan.
    Initializes the pool on startup and closes it on shutdown.
    """
    global redis_pool
    print("Initializing Redis connection pool...")
    try:
        # Create connection pool without the timeout parameter
        connection_url = f"redis://default:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}"
        redis_pool = ConnectionPool.from_url(
            connection_url,
            max_connections=20  # Set appropriate max connections
        )
        # Test the connection
        client = AsyncRedis(connection_pool=redis_pool)
        await asyncio.wait_for(client.ping(), timeout=5.0)
        print("Redis connection pool created and connection successful.")
    except Exception as e:
        print(f"Failed to connect to Redis or create pool: {e}")
        redis_pool = None
        # Don't raise an exception - allow app to start without Redis

    yield
    # Shutdown: Disconnect the pool
    if redis_pool:
        print("Closing Redis connection pool...")
        redis_pool.disconnect()
        print("Redis connection pool closed.")
async def get_redis() -> AsyncRedis:
    """
    Dependency that provides an async Redis client using the shared pool.
    Falls back gracefully if Redis is unavailable.
    """
    if redis_pool is None:
        # Return a mock Redis client that does nothing
        return None
    
    # Create a client instance using the shared pool for this request
    return AsyncRedis(connection_pool=redis_pool)