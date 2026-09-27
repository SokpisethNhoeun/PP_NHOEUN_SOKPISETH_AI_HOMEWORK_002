import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
load_dotenv(Path(__file__).with_name(".env"), override=False)

DDL = """
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    category VARCHAR(100) NOT NULL,
    price NUMERIC(10,2) NOT NULL,
    stock INTEGER NOT NULL
)
"""


class Database:
    def __init__(self):
        self.settings = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "6432"),
            "dbname": os.getenv("DB_NAME", "shopping_agent"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", ""),
        }

    def query(self, sql, params=()):
        with psycopg.connect(**self.settings, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params)

                if cursor.description:
                    rows = cursor.fetchall()

                    for row in rows:
                        if "price" in row:
                         row["price"] = float(row["price"])

                    return rows

            return []

    def initialize(self):
        self.query(DDL)

    def search(self, name):
        return self.query(
            """
            SELECT id, name, category, price, stock
            FROM products
            WHERE name ILIKE %s
            """,
            (f"%{name}%",),
        )

    def get(self, product_id):
        rows = self.query(
            """
            SELECT id, name, category, price, stock
            FROM products
            WHERE id = %s
            """,
            (product_id,),
        )

        return rows[0] if rows else None


    def delete(self, product_id):
        self.query(
            "DELETE FROM products WHERE id = %s",
            (product_id,),
        )
    
if __name__ == "__main__":
    db = Database()
    db.initialize()

    print("Database ready!")