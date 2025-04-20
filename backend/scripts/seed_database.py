from faker import Faker
import random
import csv
import time
from sqlalchemy import create_engine
from app.core.config import settings

fake = Faker()
categories = ['electronics', 'clothing', 'books', 'home', 'toys']

def seed_database():
    start_time = time.time()

    # Create engine
    engine = create_engine(settings.DATABASE_URL)

    # Generate fake data and write to CSV
    csv_file = 'products.csv'
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'description', 'price', 'category', 'stock_quantity', 'created_at', 'updated_at'])
        for _ in range(95_000):
            writer.writerow([
                fake.catch_phrase().replace("'", "''"),  # Escape single quotes for SQL
                fake.paragraph().replace("'", "''"),
                round(random.uniform(10, 1000), 2),
                random.choice(categories),
                random.randint(0, 100),
                fake.date_time_this_decade().isoformat(),
                fake.date_time_this_decade().isoformat()
            ])

    # Use COPY to load data
    with engine.connect() as conn:
        with conn.begin():  # Start transaction
            conn.execute("TRUNCATE TABLE products CASCADE;")  # Clear table if needed
            with open(csv_file, 'r') as f:
                conn.connection.cursor().copy_expert(
                    """
                    COPY products (name, description, price, category, stock_quantity, created_at, updated_at)
                    FROM STDIN WITH (FORMAT CSV, HEADER TRUE)
                    """,
                    f
                )

    end_time = time.time()
    print(f"Database seeded with 95,000 products in {end_time - start_time:.2f} seconds.")

if __name__ == "__main__":
    seed_database()