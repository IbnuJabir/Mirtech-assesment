from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from redis import Redis
from app.db.base import SessionLocal
from app.core.config import settings

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Redis dependency
def get_redis():
    redis_client = Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, decode_responses=True,  password=settings.REDIS_PASSWORD)
    try:
        yield redis_client
    finally:
        redis_client.close()