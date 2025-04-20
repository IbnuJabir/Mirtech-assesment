from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    # Original database URL for synchronous operations
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    
    # PostgreSQL connection parameters
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "postgres")
    
    # Convert standard PostgreSQL URL to async format
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        # Replace 'postgresql://' with 'postgresql+asyncpg://'
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        return self.DATABASE_URL
    
    # Redis configuration
    REDIS_HOST: str = os.getenv("REDIS_HOST")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT"))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", None)
    
    # Database connection pool settings
    DATABASE_POOL_SIZE: int = int(os.getenv("DATABASE_POOL_SIZE", "20"))
    DATABASE_MAX_OVERFLOW: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "10"))
    
    # Cache settings
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "600"))
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        # Add extra to allow Pydantic v2 to accept additional fields
        extra = "ignore"  # This will ignore extra fields instead of failing

settings = Settings()
