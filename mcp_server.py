"""MCP entry point for the safe, read-only shopping tools.

The MCP server intentionally exposes product lookup and stock lookup only.
Product deletion remains behind the application's local admin harness, which
performs search-based target resolution and terminal human approval.
"""

import logging
from threading import Lock
from typing import Any, Callable

from mcp.server import MCPServer
from pydantic import BaseModel, ValidationError

from database import Database
from schemas import CheckStockInput, SearchProductsInput, error
from tools import ShoppingTools


logger = logging.getLogger(__name__)

mcp = MCPServer(
    "safe-shopping",
    instructions=(
        "Read-only product lookup tools for the Safe Shopping Agent. "
        "Deletion is handled by the local admin harness."
    ),
)

_database = Database()
_shopping_tools = ShoppingTools(_database)
_database_ready = False
_database_lock = Lock()


def _ensure_database() -> None:
    """Initialize the database once, on the first MCP tool call."""

    global _database_ready

    if _database_ready:
        return

    with _database_lock:
        if not _database_ready:
            _database.initialize()
            _database_ready = True


def _run_tool(
    schema: type[BaseModel],
    payload: dict[str, Any],
    operation: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Validate and run a shopping operation without leaking exceptions."""

    try:
        values = schema.model_validate(payload).model_dump()
    except (ValidationError, TypeError, ValueError):
        return error(
            "INVALID_INPUT",
            "Arguments must match the tool schema exactly.",
        )

    try:
        _ensure_database()
        return operation(**values)
    except Exception:
        logger.exception("MCP shopping tool failed")
        return error(
            "TOOL_ERROR",
            "Tool failed safely; no raw exception is exposed.",
        )


@mcp.tool()
def search_products(query: str) -> dict[str, Any]:
    """Search products by name and return product details and stock."""

    return _run_tool(
        SearchProductsInput,
        {"query": query},
        _shopping_tools.search_products,
    )


@mcp.tool()
def check_stock(product_id: int) -> dict[str, Any]:
    """Return the current stock for a product ID."""

    return _run_tool(
        CheckStockInput,
        {"product_id": product_id},
        _shopping_tools.check_stock,
    )


if __name__ == "__main__":
    # stdio is the local MCP default. The host launches this process and
    # exchanges JSON-RPC messages over stdin/stdout.
    mcp.run()
