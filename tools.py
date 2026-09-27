from schemas import ok, error


class ShoppingTools:
    def __init__(self, database):
        self.db = database

    def search_products(self, query):
        products = self.db.search(query)

        return ok({
        "products": products[:10],
        "has_more": len(products) > 10
    })

    def check_stock(self, product_id):
        product = self.db.get(product_id)

        if product is None:
            return error("PRODUCT_NOT_FOUND", "Product not found.")

        return ok({
            "id": product["id"],
            "name": product["name"],
            "stock": product["stock"]
        })

    def delete_product(self, product_id):
        product = self.db.get(product_id)

        if product is None:
            return error("PRODUCT_NOT_FOUND", "Product not found.")

        self.db.delete(product_id)

        return ok({
            "deleted": True,
            "name": product["name"]
        })
