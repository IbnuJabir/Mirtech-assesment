from sqlalchemy import Column, Integer, String, Float, DateTime
from app.db.base import Base

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(String)
    price = Column(Float, index=True)
    category = Column(String, index=True)
    stock_quantity = Column(Integer)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    # search_vector = Column(TSVECTOR)  # Uncomment if using full-text search