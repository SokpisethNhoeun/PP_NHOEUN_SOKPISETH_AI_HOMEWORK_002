import json
import os

from dotenv import load_dotenv
from ollama import Client

from database import Database
from harness import Harness
from schemas import error, tool_schemas
from tools import ShoppingTools


load_dotenv()

MAX_MODEL_CALLS = 3


SYSTEM_PROMPT = """
You are a shopping assistant.

Rules:
- Use the provided tools when needed.
- Use the tool-calling interface for actions; do not write a function call as normal text.
- Use only one tool per response.
- Search by product name or ID.
- search_products returns product ID, name, category, price, and stock.
- When the user asks which matching products are in stock, list EVERY returned product whose stock is greater than 0.
- Do not omit products from tool results.
- Never invent a product ID or stock value.
- Search before deleting by product name.
- Never say a product was deleted unless the tool confirms it.
- Keep answers short and clear.
"""


def parse_text_tool_call(content):
    """Parse a JSON-like tool request returned as normal model text.

    Some Ollama models return a function call in ``message.content`` instead
    of populating ``message.tool_calls``. The result is still sent through the
    harness, so role and input validation remain authoritative.
    """

    if not isinstance(content, str) or not content.strip():
        return None

    candidates = [content.strip()]

    # Handle a fenced JSON response and the escaped form produced by some
    # model templates, for example: {"parameters":{\"product_id\":1}}.
    stripped = content.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        candidates.append("\n".join(lines[1:-1]).strip())

    candidates.append(
        content.strip()
        .replace("\\\"", '"')
        .replace("\\{", "{")
        .replace("\\}", "}")
    )

    for candidate in candidates:
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue

        # Occasionally the whole JSON object is wrapped in a JSON string.
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                continue

        if not isinstance(value, dict):
            continue

        name = value.get("name")
        arguments = value.get("parameters", value.get("arguments"))

        if (
            isinstance(name, str)
            and isinstance(arguments, (dict, str))
        ):
            return name, arguments

    return None


class ShoppingAgent:

    def __init__(self, role):
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2:latest")

        self.client = Client(
            host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        )

        self.db = Database()
        self.tools = ShoppingTools(self.db)
        self.harness = Harness(self.tools, role)


    def startup_check(self):
        try:
            self.db.initialize()
            self.client.show(self.model)

            return True, "Database and Ollama are ready."

        except Exception as e:
            return False, str(e)


    def run(self, request):
        if not request.strip():
            return "Please enter a request."

        self.harness.begin(request)

        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": request
            }
        ]


        for call_number in range(MAX_MODEL_CALLS):

            response = self.client.chat(
                model=self.model,
                messages=messages,
                tools=tool_schemas()
            )

            message = response.message
            tool_calls = list(message.tool_calls or [])
            text_tool_call = None


            # Model gave final answer
            if not tool_calls:
                text_tool_call = parse_text_tool_call(message.content)

                if text_tool_call is None:
                    return message.content or ""

                # Keep the model's request in the conversation before adding
                # the tool result on the next message.
                messages.append({
                    "role": "assistant",
                    "content": message.content or ""
                })
            else:
                # Save model tool request
                messages.append(message)


            # Only one tool is allowed
            if tool_calls and len(tool_calls) != 1:

                result = error(
                    "MULTIPLE_TOOL_CALLS",
                    "Use only one tool at a time."
                )

                messages.append({
                    "role": "tool",
                    "tool_name": tool_calls[0].function.name,
                    "content": json.dumps(result)
                })

                continue


            # Get requested tool
            if tool_calls:
                call = tool_calls[0]
                tool_name = call.function.name
                arguments = call.function.arguments
            else:
                tool_name, arguments = text_tool_call


            print(f"\n[Agent] Tool: {tool_name}")
            print(f"[Arguments] {arguments}")


            # Harness checks the tool
            result = self.harness.execute(
                tool_name,
                arguments
            )


            print("[Result]")
            print(
                json.dumps(
                    result,
                    indent=2,
                    default=str
                )
            )


            # If tool failed, return exact error
            if not result["ok"]:
                return result["error"]["message"]


            # Give successful result back to Ollama
            messages.append({
                "role": "tool",
                "tool_name": tool_name,
                "content": json.dumps(
                    result,
                    default=str
                )
            })


        return "Maximum model calls reached."
