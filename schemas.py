from enum import Enum
from pydantic import BaseModel, Field


class Role(str, Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"


class SearchProductsInput(BaseModel):
    query: str = Field(
        min_length=1,
        max_length=100
    )


class CheckStockInput(BaseModel):
    product_id: int = Field(gt=0)


class DeleteProductInput(BaseModel):
    product_id: int = Field(gt=0)


INPUTS = {
    "search_products": SearchProductsInput,
    "check_stock": CheckStockInput,
    "delete_product": DeleteProductInput,
}


DESCRIPTIONS = {
    "search_products": "Search product by ID or name.",
    "check_stock": "Check product stock by ID.",
    "delete_product": "Delete product by ID.",
}


def tool_schemas():
    tools = []

    for name, schema in INPUTS.items():
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": DESCRIPTIONS[name],
                "parameters": schema.model_json_schema(),
            }
        })

    return tools


def ok(data):
    return {
        "ok": True,
        "data": data
    }


def error(code, message):
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message
        }
    }