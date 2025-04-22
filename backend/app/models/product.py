from sqlalchemy import Column, Integer, String, Float, DateTime, Index, text
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import FunctionElement
from app.db.base import Base

# Custom GIN index for full-text search if PostgreSQL
class tsvector(FunctionElement):
    name = 'to_tsvector'
    inherit_cache = True

@compiles(tsvector, 'postgresql')
def compile_tsvector(element, compiler, **kw):
    return "%s('english', %s)" % (element.name, compiler.process(element.clauses))

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    price = Column(Float, index=True)
    category = Column(String, index=True)
    stock_quantity = Column(Integer)
    created_at = Column(DateTime, index=True)
    updated_at = Column(DateTime)
    
    # Create composite indexes for common query patterns
    __table_args__ = (
        # Index for category + sorting by price
        Index('idx_category_price', category, price),
        
        # Index for category + sorting by name
        Index('idx_category_name', category, name),
        
        # Index for pagination + sorting
        Index('idx_created_at_id', created_at, id),
    )
    
    @classmethod
    async def create_text_search_index(cls, engine):
        """
        Creates a GIN index for full-text search on PostgreSQL
        Call this method during application startup
        """
        # SQL to create a GIN index for full-text search
        sql = """
        DO $$
        BEGIN
            -- Check if the column exists
            IF NOT EXISTS (
                SELECT FROM pg_attribute
                WHERE attrelid = 'products'::regclass
                AND attname = 'search_vector'
            ) THEN
                -- Add a tsvector column if it doesn't exist
                ALTER TABLE products ADD COLUMN search_vector tsvector;
                
                -- Create an index on the tsvector column
                CREATE INDEX idx_products_search_vector ON products USING GIN (search_vector);
                
                -- Create a trigger to update the tsvector column
                CREATE OR REPLACE FUNCTION products_search_vector_update() RETURNS trigger AS $$
                BEGIN
                    NEW.search_vector := to_tsvector('english', 
                        coalesce(NEW.name, '') || ' ' || 
                        coalesce(NEW.description, '') || ' ' || 
                        coalesce(NEW.category, '')
                    );
                    RETURN NEW;
                END
                $$ LANGUAGE plpgsql;
                
                -- Create trigger
                CREATE TRIGGER products_search_vector_update_trigger
                BEFORE INSERT OR UPDATE ON products
                FOR EACH ROW EXECUTE FUNCTION products_search_vector_update();
                
                -- Update existing records
                UPDATE products SET search_vector = to_tsvector('english',
                    coalesce(name, '') || ' ' || 
                    coalesce(description, '') || ' ' || 
                    coalesce(category, '')
                );
            END IF;
        END
        $$;
        """
        
        # Execute the SQL to create the index
        async with engine.begin() as conn:
            await conn.execute(text(sql))
            print("Full-text search index created or verified")