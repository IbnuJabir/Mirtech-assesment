from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from redis.asyncio import Redis as AsyncRedis, ConnectionPool
from app.core.config import settings
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends # Import Request and Depends

# SQLAlchemy Async Setup (remains largely the same)
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
    """Dependency to get async SQLAlchemy session."""
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()

# --- Redis Setup using app.state and Lazy Initialization ---

# Helper functions for clear initialization and closing
async def _initialize_redis_pool(redis_url: str) -> ConnectionPool:
    """Helper to initialize the pool and test connection."""
    print("Attempting to initialize Redis connection pool...")
    print(f"Using Redis URL: {redis_url}")
    try:
        pool = ConnectionPool.from_url(redis_url)
        # Test the connection
        client = AsyncRedis(connection_pool=pool)
        await client.ping()
        print("Redis connection pool created and connection successful.")
        return pool
    except Exception as e:
        print(f"Failed to connect to Redis or create pool: {e}")
        # Re-raise the exception so the calling code can handle it (e.g., raise HTTPException)
        raise

async def _close_redis_pool(pool: ConnectionPool | None):
    """Helper to close the pool."""
    if pool:
        print("Closing Redis connection pool...")
        try:
            # The disconnect method on ConnectionPool should handle closing connections
            pool.disconnect()
            print("Redis connection pool closed.")
        except Exception as e:
            print(f"Error closing Redis connection pool: {e}")

# Lifespan context manager - primarily for graceful shutdown.
# Initialization is handled lazily in the get_redis dependency for serverless robustness.
@asynccontextmanager
async def redis_lifespan(app: FastAPI):
     """
     Context manager for Redis connection pool lifespan.
     Primarily handles graceful shutdown.
     Initialization is lazy within the get_redis dependency.
     """
        # Startup logic
     app.state.redis_pool = None
     print("Redis lifespan startup phase.")

     yield # Application runs

     # Shutdown logic
     print("Redis lifespan shutdown phase.")
     await _close_redis_pool(app.state.redis_pool)


# Dependency function to get the Redis client
async def get_redis(request: Request) -> AsyncRedis:
    """
    Dependency that provides an async Redis client.
    Initializes the pool lazily on first access for a given instance and stores in app.state.
    """
    # Check if the pool is already initialized and stored in app.state for this instance
    # Use hasattr and check for None defensively
    if not hasattr(request.app.state, 'redis_pool') or request.app.state.redis_pool is None:
        print("Redis pool not found in app.state or is None. Attempting lazy initialization within get_redis.")
        try:
            # Initialize the pool and store it in app.state
            # This happens only on the first call to get_redis for this function instance
            request.app.state.redis_pool = await _initialize_redis_pool(settings.REDIS_URL)
        except Exception as e:
            # If initialization fails, raise an HTTPException
            print(f"Lazy Redis initialization failed in get_redis: {e}")
            raise HTTPException(status_code=503, detail="Redis service unavailable due to initialization failure")

    # We should now have a pool in app.state. Ensure it's not None just in case.
    if request.app.state.redis_pool is None:
         # This case should ideally not be reached if _initialize_redis_pool raises on failure,
         # but it's a safety check.
         print("ERROR: Redis connection pool is still None after lazy initialization attempt in get_redis.")
         raise HTTPException(status_code=503, detail="Redis service unavailable - pool is None after init")


    # Get a client from the pool stored in app.state
    # Print message *after* successful pool access/init
    print("Providing Redis client from app.state pool.")
    return AsyncRedis(connection_pool=request.app.state.redis_pool)