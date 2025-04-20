from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from redis.asyncio import Redis as AsyncRedis, ConnectionPool
# from redis import Redis # Keep if sync version is truly needed elsewhere
from app.db.base import Base, SessionLocal 
from app.core.config import settings
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException

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
        redis_pool = ConnectionPool.from_url(
            f"redis://default:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:{settings.REDIS_PORT}",
            # host=settings.REDIS_HOST, 
            # port=settings.REDIS_PORT, 
            # password=settings.REDIS_PASSWORD,
            decode_responses=False,
            max_connections=20
        )
        # Test the connection
        client = AsyncRedis(connection_pool=redis_pool)
        await client.ping()
        print("Redis connection pool created and connection successful.")
    except Exception as e:
        print(f"Failed to connect to Redis or create pool: {e}")
        redis_pool = None

    yield
    # Shutdown: Disconnect the pool
    if redis_pool:
        print("Closing Redis connection pool...")
        redis_pool.disconnect()
        print("Redis connection pool closed.")

async def get_redis() -> AsyncRedis:
    """
    Dependency that provides an async Redis client using the shared pool.
    Handles the case where the pool might not be available.
    """
    if redis_pool is None:
        print("ERROR: Redis connection pool is not available.")
        raise HTTPException(status_code=503, detail="Redis service unavailable")

    # Create a client instance using the shared pool for this request
    return AsyncRedis(connection_pool=redis_pool)