from fastapi import FastAPI
from app.api.v1.endpoints import products
from app.db.base import Base, engine, async_engine
from fastapi.middleware.cors import CORSMiddleware
from app.core.dependencies import redis_lifespan
from app.models.product import Product
import asyncio

app = FastAPI(
    title="Mirtech - High-Performance Data Table API",
    description="FastAPI backend for handling 100,000+ records",
    version="1.0.0",
    lifespan=redis_lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","https://api-mirtech.vercel.app", "https://mirtech.vercel.app" ,"http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables
Base.metadata.create_all(bind=engine)

# Initialize database optimizations
@app.on_event("startup")
async def setup_database():
    # Create full-text search indexes
    await Product.create_text_search_index(async_engine)
    print("Database optimizations applied")

app.include_router(products.router, prefix="/api/v1", tags=["products"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Mirtech - The High-Performance Data Table API"}