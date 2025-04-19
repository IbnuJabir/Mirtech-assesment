from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

# Create synchronous engine
engine = create_engine(settings.DATABASE_URL)

# Create async engine (will use asyncpg driver)
async_engine = create_async_engine(
    settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10
)

# Synchronous Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Asynchronous Session factory
AsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    class_=AsyncSession
)

# Base class
class Base(DeclarativeBase):
    pass