from pydantic import BaseModel, validator, Field
from typing import Optional, List
from datetime import datetime

class ProductQuery(BaseModel):
    """
    Query parameters for product listings endpoint
    
    Includes validation for all parameters to ensure proper API usage
    """
    page: int = Field(default=1, ge=1, description="Page number (minimum 1)")
    limit: int = Field(default=50, ge=1, le=100, description="Items per page (between 1 and 100)")
    sort_by: str = Field(default="id", description="Field to sort results by")
    sort_order: str = Field(default="asc", description="Sort direction (asc or desc)")
    category: Optional[str] = Field(default=None, description="Filter by product category")
    search: Optional[str] = Field(default=None, description="Search term")

    @validator("sort_by")
    def sort_by_must_be_valid(cls, v):
        valid_fields = ["id", "name", "price", "category", "stock_quantity", "created_at", "updated_at"]
        if v not in valid_fields:
            raise ValueError(f"Sort_by must be one of {valid_fields}")
        return v

    @validator("sort_order")
    def sort_order_must_be_valid(cls, v):
        if v not in ["asc", "desc"]:
            raise ValueError("Sort_order must be 'asc' or 'desc'")
        return v
        
    @validator("category")
    def validate_category(cls, v):
        if v is not None:
            if len(v.strip()) == 0:
                raise ValueError("Category cannot be an empty string")
            if len(v) > 50:
                raise ValueError("Category value is too long (max 50 characters)")
        return v
    
    @validator("search")
    def validate_search(cls, v):
        if v is not None:
            if len(v.strip()) == 0:
                raise ValueError("Search term cannot be an empty string")
            if len(v) > 100:
                raise ValueError("Search term is too long (max 100 characters)")
        return v

class ProductOut(BaseModel):
    id: int
    name: str
    description: str
    price: float
    category: str
    stock_quantity: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Correct for Pydantic 2.x with SQLAlchemy

class PaginatedProducts(BaseModel):
    data: List[ProductOut]
    total_count: int
    page: int
    limit: int