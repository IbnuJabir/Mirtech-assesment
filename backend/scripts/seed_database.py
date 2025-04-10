from faker import Faker
import random
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import time

fake = Faker()
categories = ['electronics', 'clothing', 'books', 'home', 'toys']

def seed_database():
    # Start timing
    start_time = time.time()

    # Create engine and session factory
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)

    # Generate fake data
    products = []
    for _ in range(100_000):
        product = {
            "name": fake.catch_phrase(),
            "description": fake.paragraph(),
            "price": round(random.uniform(10, 1000), 2),
            "category": random.choice(categories),
            "stock_quantity": random.randint(0, 100),
            "created_at": fake.date_time_this_decade(),
            "updated_at": fake.date_time_this_decade(),
        }
        products.append(product)

    # Bulk insert with SQLAlchemy 2.0
    with Session() as session:
        session.execute(
            text(
                "INSERT INTO products (name, description, price, category, stock_quantity, created_at, updated_at) "
                "VALUES (:name, :description, :price, :category, :stock_quantity, :created_at, :updated_at)"
            ),
            products
        )
        session.commit()

    # End timing and report
    end_time = time.time()
    print(f"Database seeded with 100,000 products in {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    seed_database()