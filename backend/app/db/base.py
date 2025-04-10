from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create engine
engine = create_engine(settings.DATABASE_URL)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class remains declarative_base for now (or update to Mapped if using ORM)
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass