from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, Index, text
from app.core.dependencies import get_async_db, get_redis
from app.schemas.product import ProductQuery, PaginatedProducts, ProductOut
from app.models.product import Product
from redis.asyncio import Redis
import msgpack
from datetime import datetime, timedelta
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pydantic import ValidationError

router = APIRouter()

# Improved cache configuration
CACHE_TTL_SECONDS = 600
CACHE_PREFIX = "products:"
REDIS_TIMEOUT = 3.0  # Increased timeout for Redis operations

# Custom msgpack handlers for datetime objects
def encode_datetime(obj):
    if isinstance(obj, datetime):
        return {"__datetime__": True, "value": obj.isoformat()}
    return obj

def decode_datetime(obj):
    if isinstance(obj, dict) and obj.get("__datetime__"):
        return datetime.fromisoformat(obj["value"])
    return obj

# Simplified cache key generation for better performance
def generate_cache_key(query_params: Dict[str, Any]) -> str:
    # Extract only the parameters that affect the query results
    key_parts = [
        f"p{query_params.get('page', 1)}",
        f"l{query_params.get('limit', 50)}",
        f"s{query_params.get('sort_by', 'id')}",
        f"d{query_params.get('sort_order', 'asc')}"
    ]
    
    # Add optional filters only if they exist
    if category := query_params.get('category'):
        key_parts.append(f"c{category}")
    
    if search := query_params.get('search'):
        key_parts.append(f"q{search}")
    
    # Build compact key
    return f"{CACHE_PREFIX}{'_'.join(key_parts)}"

async def get_from_cache(redis_client: Redis, cache_key: str) -> Optional[bytes]:
    """Get data from cache with optimized error handling"""
    try:
        return await asyncio.wait_for(
            redis_client.get(cache_key),
            timeout=REDIS_TIMEOUT
        )
    except (asyncio.TimeoutError, Exception):
        # Simplified error handling - just return None on any error
        return None

async def set_to_cache(redis_client: Redis, cache_key: str, value: bytes, ttl: int) -> None:
    """Set data to cache without waiting for result"""
    try:
        await redis_client.set(cache_key, value, ex=ttl)
    except Exception:
        # Silently continue on error - caching is a performance optimization, not critical
        pass

@router.get("/products", response_model=PaginatedProducts)
async def get_products(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_async_db),
    redis_client: Redis = Depends(get_redis),
    page: int = 1,
    limit: int = 50,
    sort_by: str = "id",
    sort_order: str = "asc",
    category: str = None,
    search: str = None
):
    """
    Get paginated list of products with optional filtering - optimized version.
    """
    start_time = datetime.now()
    
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
            error_details = []
            for error in e.errors():
                field = error["loc"][0]
                msg = error["msg"]
                error_details.append(f"{field}: {msg}")
            
            raise HTTPException(
                status_code=400,
                detail=f"Invalid query parameters: {'; '.join(error_details)}"
            )

        # Set default cache status
        response.headers["X-Cache"] = "MISS"
        
        # Generate optimized cache key
        cache_key = generate_cache_key(query.model_dump())
        
        # Try to get data from cache first - skip connection check to improve performance
        cached_data = await get_from_cache(redis_client, cache_key)
        
        if cached_data:
            try:
                # Deserialize with msgpack
                unpacked_data = msgpack.unpackb(cached_data, object_hook=decode_datetime)
                result = PaginatedProducts.model_validate(unpacked_data)
                response.headers["X-Cache"] = "HIT"
                
                # Add timing information
                process_time = (datetime.now() - start_time).total_seconds() * 1000
                response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
                
                return result
            except Exception:
                # Continue to fetch from DB on deserialization error
                pass
        
        # Optimize database query with raw SQL for performance
        # This is more efficient for large datasets than the ORM approach
        if query.search:
            # If search is provided, use a more optimized query with ILIKE
            search_term = f"%{query.search}%"
            
            # For count
            count_sql = """
            SELECT COUNT(*) 
            FROM products 
            WHERE 1=1
            """
            count_params = {}
            
            if query.category:
                count_sql += " AND category = :category"
                count_params['category'] = query.category
                
            if query.search:
                count_sql += " AND name ILIKE :search"
                count_params['search'] = search_term
                
            count_result = await db.execute(text(count_sql), count_params)
            total_count = count_result.scalar()
            
            # For data
            data_sql = """
            SELECT id, name, description, price, category, stock_quantity, created_at, updated_at
            FROM products
            WHERE 1=1
            """
            data_params = {}
            
            if query.category:
                data_sql += " AND category = :category"
                data_params['category'] = query.category
                
            if query.search:
                data_sql += " AND name ILIKE :search"
                data_params['search'] = search_term
            
            # Add sorting
            data_sql += f" ORDER BY {query.sort_by} {query.sort_order.upper()}"
            
            # Add pagination
            offset = (query.page - 1) * query.limit
            data_sql += " LIMIT :limit OFFSET :offset"
            data_params['limit'] = query.limit
            data_params['offset'] = offset
            
            # Execute the query
            result = await db.execute(text(data_sql), data_params)
            products = result.mappings().all()
            
        else:
            # If no search, use the ORM approach which is more readable and maintainable
            # Build database query
            stmt = select(Product)
            
            # Apply filters
            if query.category:
                stmt = stmt.where(Product.category == query.category)
                
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
            count_stmt = select(func.count()).select_from(Product)
            if query.category:
                count_stmt = count_stmt.where(Product.category == query.category)
            
            # Execute count query
            result = await db.execute(count_stmt)
            total_count = result.scalar()
            
            # Apply pagination
            offset = (query.page - 1) * query.limit
            stmt = stmt.offset(offset).limit(query.limit)
            
            # Execute query
            result = await db.execute(stmt)
            products = result.scalars().all()
        
        # Prepare response data
        if isinstance(products, list) and products and hasattr(products[0], '__table__'):
            # Handle ORM objects
            product_data = [ProductOut.model_validate(product).model_dump() for product in products]
        else:
            # Handle raw SQL results (mappings)
            product_data = [dict(p) for p in products]
            # Convert datetime objects properly
            for p in product_data:
                if 'created_at' in p and p['created_at']:
                    if not isinstance(p['created_at'], datetime):
                        p['created_at'] = datetime.fromisoformat(str(p['created_at']))
                if 'updated_at' in p and p['updated_at']:
                    if not isinstance(p['updated_at'], datetime):
                        p['updated_at'] = datetime.fromisoformat(str(p['updated_at']))
        
        response_data = {
            "data": product_data,
            "total_count": total_count,
            "page": query.page,
            "limit": query.limit
        }
        
        # Cache result asynchronously without waiting
        try:
            serialized_data = msgpack.packb(response_data, default=encode_datetime)
            # Don't await here - fire and forget to improve response time
            asyncio.create_task(set_to_cache(
                redis_client, 
                cache_key, 
                serialized_data,
                CACHE_TTL_SECONDS
            ))
        except Exception:
            # Continue without caching on error
            pass
        
        result = PaginatedProducts(**response_data)
        
        # Add timing information
        process_time = (datetime.now() - start_time).total_seconds() * 1000
        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
        
        return result
        
    except Exception as e:
        # Log the error but don't expose details
        if not isinstance(e, HTTPException):
            raise HTTPException(
                status_code=500, 
                detail="An unexpected error occurred while processing your request"
            )
        raise