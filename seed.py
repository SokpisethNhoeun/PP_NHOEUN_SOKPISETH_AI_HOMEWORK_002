from database import Database


SAMPLES = [
    ("Samsung Galaxy S24", "Phone", "799.00", 5),
    ("Samsung Galaxy S24 Ultra", "Phone", "1299.00", 3),
    ("Samsung Galaxy A55", "Phone", "449.00", 8),
    ("iPhone 15", "Phone", "799.00", 6),
    ("iPhone 15 Pro", "Phone", "999.00", 4),
    ("iPhone 15 Pro Max", "Phone", "1199.00", 2),
]


def main():
    db = Database()
    db.initialize()

    for product in SAMPLES:
        db.add(*product)

    print("Sample products inserted!")


if __name__ == "__main__":
    main()