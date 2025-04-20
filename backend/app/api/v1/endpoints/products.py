from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.dependencies import get_async_db, get_redis
from app.schemas.product import ProductQuery, PaginatedProducts, ProductOut
from app.models.product import Product
from redis.asyncio import Redis
import msgpack
from datetime import datetime
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pydantic import ValidationError

router = APIRouter()

# Constants for cache configuration
CACHE_TTL_SECONDS = 600
CACHE_PREFIX = "products:"
REDIS_TIMEOUT = 1.0  # 1 second timeout for Redis operations

# Custom msgpack handlers for datetime objects
def encode_datetime(obj):
    if isinstance(obj, datetime):
        return {"__datetime__": True, "value": obj.isoformat()}
    return obj

def decode_datetime(obj):
    if isinstance(obj, dict) and obj.get("__datetime__"):
        return datetime.fromisoformat(obj["value"])
    return obj

async def check_redis_connection(redis_client: Redis) -> Tuple[bool, str]:
    """Test if Redis connection is working"""
    try:
        await asyncio.wait_for(
            redis_client.ping(),
            timeout=REDIS_TIMEOUT
        )
        return True, "Connection successful"
    except asyncio.TimeoutError:
        return False, "Connection timeout"
    except Exception as e:
        return False, f"Connection error: {str(e) or type(e).__name__}"

async def get_from_cache(redis_client: Redis, cache_key: str) -> Optional[bytes]:
    """Get data from cache with timeout protection"""
    try:
        # Set a timeout for the Redis operation
        return await asyncio.wait_for(
            redis_client.get(cache_key),
            timeout=REDIS_TIMEOUT
        )
    except asyncio.TimeoutError:
        print("Redis get operation timed out")
        return None
    except Exception as e:
        error_message = str(e) if str(e) else type(e).__name__
        print(f"Redis get error: {error_message}")
        return None

async def set_to_cache(redis_client: Redis, cache_key: str, value: bytes, ttl: int) -> bool:
    """Set data to cache with timeout protection"""
    try:
        # Log TTL validation
        if not isinstance(ttl, int):
            raise ValueError("TTL must be an integer (seconds)")
        print(f"Setting data to cache: {cache_key} with TTL: {ttl} seconds")

        # Log Redis client type and method type
        print(f"Redis client set method: {type(redis_client.set)}")

        # Check if redis_client.set is callable
        if not callable(redis_client.set):
            print(f"ERROR: redis_client.set is not callable! It is: {type(redis_client.set)}")
            return False

        # Set data to Redis cache with timeout protection
        await asyncio.wait_for(
            redis_client.set(cache_key, value, ex=ttl),
            timeout=REDIS_TIMEOUT
        )
        print(f"Data successfully set to cache: {cache_key}")
        return True

    except asyncio.TimeoutError:
        print("Redis set operation timed out")
        return False
    except Exception as e:
        # Log detailed error message
        print(f"Redis set error: {e}")
        return False

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
    Get paginated list of products with optional filtering.
    """
    start_time = datetime.now()
    use_cache = True
    redis_available = False
    
    try:
        # Check if Redis is available
        if use_cache:
            is_connected, message = await check_redis_connection(redis_client)
            if not is_connected:
                print(f"Redis unavailable: {message}")
                use_cache = False
            else:
                redis_available = True
                print("Redis connection successful")
        
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

        response.headers["X-Cache"] = "MISS"
        response.headers["X-Redis-Available"] = str(redis_available)
        
        # Try to get data from cache first
        if use_cache:
            # Generate cache key
            cache_key = f"{CACHE_PREFIX}{query.json()}"
            cached_data = await get_from_cache(redis_client, cache_key)
            
            if cached_data:
                try:
                    # Try to deserialize with msgpack
                    unpacked_data = msgpack.unpackb(cached_data, object_hook=decode_datetime)
                    result = PaginatedProducts.model_validate(unpacked_data)
                    response.headers["X-Cache"] = "HIT"
                    
                    # Add timing information
                    process_time = (datetime.now() - start_time).total_seconds() * 1000
                    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
                    
                    return result
                except Exception as e:
                    print(f"Cache deserialization error: {str(e) or type(e).__name__}")
                    # Continue to fetch from DB on deserialization error
        
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
        count_stmt = select(func.count()).select_from(Product)
        if query.category:
            count_stmt = count_stmt.where(Product.category == query.category)
        if query.search:
            try:
                count_stmt = count_stmt.where(Product.search_vector.match(query.search))
            except AttributeError:
                count_stmt = count_stmt.where(Product.name.ilike(f"%{query.search}%"))
        
        # Execute count query
        result = await db.execute(count_stmt)
        total_count = result.scalar()
        
        # Apply pagination
        offset = (query.page - 1) * query.limit
        stmt = stmt.offset(offset).limit(query.limit)
        
        # Execute query
        result = await db.execute(stmt)
        products = result.scalars().all()
        
        # Prepare response
        try:
            product_data = [ProductOut.from_orm(product).dict() for product in products]
        except AttributeError:
            product_data = [ProductOut.model_validate(product).model_dump() for product in products]
        
        response_data = {
            "data": product_data,
            "total_count": total_count,
            "page": query.page,
            "limit": query.limit
        }
        
        # Try to cache result if caching is enabled
        if use_cache:
            try:
                # Use custom handler for datetime objects
                serialized_data = msgpack.packb(response_data, default=encode_datetime)
                # Cache asynchronously without waiting for result
                asyncio.create_task(set_to_cache(
                    redis_client, 
                    cache_key, 
                    serialized_data,
                    CACHE_TTL_SECONDS
                ))
            except Exception as e:
                error_message = str(e) if str(e) else type(e).__name__
                print(f"Error serializing cache data: {error_message}")
                # Continue without caching on error
        
        result = PaginatedProducts(**response_data)
        
        # Add timing information
        process_time = (datetime.now() - start_time).total_seconds() * 1000
        response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
        
        return result
        
    except Exception as e:
        # Log the error
        error_message = str(e) if str(e) else type(e).__name__
        print(f"ERROR: {error_message}")
        import traceback
        traceback.print_exc()
        
        if isinstance(e, HTTPException):
            raise
        
        raise HTTPException(
            status_code=500, 
            detail="An unexpected error occurred while processing your request"
        )