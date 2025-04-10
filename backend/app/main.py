from fastapi import FastAPI
from app.api.v1.endpoints import products
from app.db.base import Base, engine

app = FastAPI(
    title="High-Performance Data Table API",
    description="FastAPI backend for handling 100,000+ records",
    version="1.0.0"
)

# Create tables
Base.metadata.create_all(bind=engine)

app.include_router(products.router, prefix="/api/v1", tags=["products"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the High-Performance Data Table API"}