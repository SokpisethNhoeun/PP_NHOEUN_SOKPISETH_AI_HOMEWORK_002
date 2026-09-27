Safe Shopping Agent

1. Project Overview

Safe Shopping Agent is a role-aware shopping assistant that uses an Ollama language model to decide which registered shopping tool should handle a request. The tools use PostgreSQL as the source of truth for product data.

The application supports two roles:

Customer:
Can find products and check stock.

Admin:
Can find products, check stock, and delete products after the required safety checks and human approval.

The model is not allowed to change the database directly. Every action goes through the harness, which validates the requested tool, the caller's role, and the tool arguments before execution.


2. Available Tools

search_products

Purpose:
Search products by name and return up to ten matches, including each product's ID, name, category, price, and stock.

Input:
query: str


check_stock

Purpose:
Read the current stock for one product.

Input:
product_id: int


delete_product

Purpose:
Delete one product after the product has been safely resolved and the human approves the deletion.

Input:
product_id: int


search_products also returns has_more so the assistant can avoid silently treating a truncated search result as a unique match.


3. Agent Loop

The agent follows a decision -> action -> observation loop:

User request
    ↓
Model decides: final answer or one registered tool call
    ↓
Harness validates tool name, role, and arguments
    ↓
Tool performs the database action
    ↓
Harness returns the structured result as an observation
    ↓
Model uses the observation to answer the user

The model receives the tool result as a new message and may continue the loop until it produces a final answer.

Only one tool call is accepted at a time.


4. Permission Rule

Customer

Allowed actions:
search_products
check_stock


Admin

Allowed actions:
search_products
check_stock
delete_product


The harness checks the role before executing any tool.

A customer attempting to delete a product receives:

PERMISSION_DENIED

Deletion also requires a search result that resolves exactly one product, or an explicit product ID, followed by terminal approval from the human operator.


5. Safety

- Pydantic schemas validate every tool input.

- Search text has length limits.

- Product IDs must be positive integers.

- Database writes use parameterized SQL queries.

- Unknown tools, unauthorized actions, malformed JSON, and invalid arguments return structured errors instead of reaching the database.

- Tool exceptions are converted to TOOL_ERROR.

- Raw exceptions are not exposed to the user.

- Each user request may execute at most three tool calls.

- The model loop allows at most three model calls.

- Product deletion is protected against ambiguous search results, invented IDs, repeated decisions, and missing human approval.


6. Example Run

The following is a real not-found search flow.

The harness still validates and executes the tool, but the database contains no matching product:


You> give product id 2

[Agent] Tool: search_products

[Arguments]
{'query': '2'}

[Harness]
customer | search_products | GREEN

[Result]
{
  "ok": true,
  "data": {
    "products": [
      {
        "id": 2,
        "name": "Samsung Galaxy S24 Ultra",
        "category": "Phone",
        "price": 1299.0,
        "stock": 3
      }
    ],
    "has_more": false
  }
}

Assistant> Product ID 2 is for the Samsung Galaxy S24 Ultra, priced at $1299.00 and currently has 3 units in stock.


7. MCP Server

The project also exposes the safe read-only shopping tools through
`mcp_server.py`. It uses the official MCP Python SDK and the default `stdio`
transport. Product deletion is intentionally not exposed here because it must
remain protected by the local admin role, search-based target resolution, and
human approval in the harness.

Available MCP tools:

- `search_products(query)`
- `check_stock(product_id)`

Host -> Client -> Server -> Tool path:

```text
1. Host
   The LLM application (for example an IDE or desktop assistant) receives
   the user's request and decides that a shopping tool is needed.

2. Client
   The MCP client inside the host starts mcp_server.py as a subprocess and
   sends MCP JSON-RPC messages over stdin/stdout. It discovers tools with
   tools/list and requests work with tools/call.

3. Server
   MCPServer receives the request, selects the registered Python function,
   and returns a structured MCP result. The server does not talk to the model
   directly.

4. Tool
   The decorated function validates the arguments with the same Pydantic
   schemas used by the application, calls ShoppingTools, and reads PostgreSQL
   through Database. The result travels back through Server -> Client -> Host.
```

In short:

```text
Host -> MCP Client -> mcp_server.py -> search_products/check_stock -> PostgreSQL
Host <- MCP Client <- mcp_server.py <- structured result              <-
```

Run the server directly from the project virtual environment:

```bash
./.venv/bin/python mcp_server.py
```

The process waits silently because stdout is reserved for MCP protocol
messages. A host or MCP Inspector must connect to it. To launch the Inspector
with the SDK CLI, use:

```bash
./.venv/bin/mcp dev mcp_server.py
```

# PP_NHOEUN_SOKPISETH_AI_HOMEWORK_002
