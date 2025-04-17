from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.core.dependencies import get_db, get_redis
from app.schemas.product import ProductQuery, PaginatedProducts, ProductOut
from app.models.product import Product
import redis
import json
from datetime import datetime
from typing import Dict, Any
from pydantic import ValidationError

router = APIRouter()

# Helper to serialize objects correctly
def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

@router.get("/products", response_model=PaginatedProducts)
async def get_products(
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    page: int = 1,
    limit: int = 50,
    sort_by: str = "id",
    sort_order: str = "asc",
    category: str = None,
    search: str = None
):
    """
    Get paginated list of products with optional filtering.
    
    - Supports pagination with page and limit parameters
    - Allows sorting by field and direction
    - Enables filtering by category
    - Provides search functionality when available
    - Results are cached for performance
    """
    try:
        # Create and validate the query parameters
        try:
            query = ProductQuery(
                page=page,
                limit=limit,
                sort_by=sort_by,
                sort_order=sort_order,
                category=category,
                search=search
            )
        except ValidationError as e:
            # Convert Pydantic validation errors to proper API errors
            error_details = []
            for error in e.errors():
                field = error["loc"][0]
                msg = error["msg"]
                error_details.append(f"{field}: {msg}")
            
            raise HTTPException(
                status_code=400,
                detail=f"Invalid query parameters: {'; '.join(error_details)}"
            )

        # Generate cache key from query parameters
        cache_key = f"products:{query.json()}"
        
        # Try to get data from cache first
        cached_data = redis_client.get(cache_key)
        if cached_data:
            print("redis Hits")
            cached_dict = json.loads(cached_data)
            return PaginatedProducts(**cached_dict)
        print("redis misses")
        # Build database query
        stmt = select(Product)
        
        # Apply filters
        if query.category:
            stmt = stmt.where(Product.category == query.category)
            
        # Apply search if provided
        if query.search:
            try:
                # Try full-text search if available
                stmt = stmt.where(Product.search_vector.match(query.search))
            except AttributeError:
                # Fall back to LIKE search
                stmt = stmt.where(Product.name.ilike(f"%{query.search}%"))

        # Apply sorting
        try:
            order_column = getattr(Product, query.sort_by)
            if query.sort_order == "desc":
                stmt = stmt.order_by(order_column.desc())
            else:
                stmt = stmt.order_by(order_column.asc())
        except AttributeError:
            # If sort field doesn't exist, use default sorting
            stmt = stmt.order_by(Product.id.asc())
            
        # Get total count for pagination metadata
        count_stmt = _build_count_query(query)
        total_count = db.execute(count_stmt).scalar()

        # Apply pagination
        offset = (query.page - 1) * query.limit
        stmt = stmt.offset(offset).limit(query.limit)
        
        # Execute query
        products = db.execute(stmt).scalars().all()

        # Prepare response
        response_data = _prepare_response(products, total_count, query)
        
        # Cache result for 10 minutes (600 seconds)
        redis_client.setex(
            cache_key, 
            600, 
            json.dumps(response_data, default=json_serial)
        )
        
        return PaginatedProducts(**response_data)

    except redis.exceptions.RedisError as e:
        # Log the error here
        raise HTTPException(
            status_code=503, 
            detail="Cache service unavailable. Please try again later."
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Log the error here with full traceback
        raise HTTPException(
            status_code=500, 
            detail=f"An unexpected error occurred while processing your request: {str(e)}"
        )

def _build_count_query(query: ProductQuery):
    """Build a query to count total matching products"""
    count_stmt = select(func.count()).select_from(Product)
    
    if query.category:
        count_stmt = count_stmt.where(Product.category == query.category)
        
    if query.search:
        try:
            count_stmt = count_stmt.where(Product.search_vector.match(query.search))
        except AttributeError:
            count_stmt = count_stmt.where(Product.name.ilike(f"%{query.search}%"))
            
    return count_stmt

def _prepare_response(products, total_count: int, query: ProductQuery) -> Dict[str, Any]:
    """Prepare the response data structure"""
    try:
        # Try Pydantic v1 method first
        product_data = [ProductOut.from_orm(product).dict() for product in products]
    except AttributeError:
        # Fall back to Pydantic v2 method
        product_data = [ProductOut.model_validate(product).model_dump() for product in products]
    
    return {
        "data": product_data,
        "total_count": total_count,
        "page": query.page,
        "limit": query.limit
    }
