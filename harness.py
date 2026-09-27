import json
import re

from pydantic import ValidationError

from schemas import INPUTS, Role, error


# Maximum tool calls the AI can make for one request
MAX_TOOL_CALLS = 3


# What each role can do
PERMISSIONS = {
    Role.CUSTOMER: {
        "search_products",
        "check_stock",
    },

    Role.ADMIN: {
        "search_products",
        "check_stock",
        "delete_product",
    },
}


# Risk level for each tool
RISK = {
    "search_products": "GREEN",
    "check_stock": "GREEN",
    "delete_product": "RED",
}


def terminal_approval(product):
    """Ask the human before deleting a product."""


    print("\nProduct to delete:")
    print(f"ID:       {product['id']}")
    print(f"Name:     {product['name']}")
    print(f"Category: {product['category']}")
    print(f"Price:    ${float(product['price']):.2f}")
    print(f"Stock:    {product['stock']}")

    try:  
        answer = input("Delete this product? [y/N]: ")
        return answer.strip().lower() in ["y", "yes"]

    except (EOFError, KeyboardInterrupt):
        return False


class Harness:

    def __init__(
        self,
        tools,
        role,
        approve=terminal_approval,
        trace=print
    ):
        self.tools = tools
        self.role = Role(role)
        self.approve = approve
        self.trace = trace

        self.begin("")

    def begin(self, request):
        """Start a new user request."""

        self.calls = 0
        self.candidates = []
        self.ambiguous = False
        self.deletion_closed = False

        # Detect commands such as:
        # delete 5
        # delete product 5
        # delete id 5
        # delete product id 5

        match = re.fullmatch(
            r"\s*delete\s+(?:(?:product\s+id|product|id)\s+)?([1-9][0-9]*)[.!]?\s*",
            request,
            flags=re.IGNORECASE,
        )

        if match:
            self.explicit_id = int(match.group(1))
        else:
            self.explicit_id = None

    def execute(self, name, arguments):
        """Run a tool safely."""

        # 1. Check tool-call limit
        if self.calls >= MAX_TOOL_CALLS:
            return error(
                "TOOL_LIMIT_REACHED",
                "This run has used its tool-call budget."
            )

        self.calls += 1


        # 2. Check if the tool exists
        if not isinstance(name, str) or name not in INPUTS:
            return error(
                "TOOL_NOT_ALLOWED",
                "This tool is not registered."
            )


        # 3. Check role permission
        if name not in PERMISSIONS[self.role]:
            return error(
                "PERMISSION_DENIED",
                "Your role cannot perform this action."
            )


        # 4. Validate arguments
        try:

            # AI may send arguments as JSON text
            if isinstance(arguments, str):

                if len(arguments) > 4096:
                    return error(
                        "INVALID_INPUT",
                        "Tool arguments are too large."
                    )

                arguments = json.loads(arguments)

            # Validate using Pydantic
            validated = INPUTS[name].model_validate(arguments)

            values = validated.model_dump()

        except (ValidationError, ValueError, TypeError):

            return error(
                "INVALID_INPUT",
                "Arguments must match the tool schema exactly."
            )


        # Show which tool is running
        self.trace(
            f"[Harness] {self.role.value} | "
            f"{name} | {RISK[name]}"
        )


        # 5. Run the tool
        try:

            if name == "search_products":

                result = self.tools.search_products(**values)

                if result["ok"]:

                    self.candidates = result["data"]["products"]


                    if (
                        len(self.candidates) > 1
                        or result["data"]["has_more"]
                    ):
                        self.ambiguous = True

                return result


            if name == "check_stock":

                return self.tools.check_stock(**values)


            if name == "delete_product":

                return self._delete(
                    values["product_id"]
                )




        except Exception:

            return error(
                "TOOL_ERROR",
                "Tool failed safely; no raw exception is exposed."
            )

    def _delete(self, product_id):
        """Safely delete one product."""

        # Do not allow deletion twice
        if self.deletion_closed:

            return error(
                "ACTION_ALREADY_DECIDED",
                "Deletion was already approved or rejected this run."
            )


        # User directly wrote:
        #
        # delete 5
        #
        if self.explicit_id is not None:

            if product_id != self.explicit_id:

                return error(
                    "TARGET_MISMATCH",
                    "The proposed ID differs from the user's explicit ID."
                )


        # Search returned multiple products
        elif self.ambiguous:

            return error(
                "AMBIGUOUS_PRODUCT",
                "Ask the user to choose an ID, then start a new request: Delete product ID."
            )


        # AI must search and find exactly one product first
        elif (
            len(self.candidates) != 1
            or self.candidates[0]["id"] != product_id
        ):

            return error(
                "TARGET_NOT_RESOLVED",
                "Search first; do not invent a product ID."
            )


        # Get the real product from database
        product = self.tools.db.get(product_id)

        if product is None:

            return error(
                "PRODUCT_NOT_FOUND",
                "No product has that ID."
            )


        # After this point, don't ask twice
        self.deletion_closed = True


        # Ask human for approval
        if not self.approve(product):

            return error(
                "HUMAN_REJECTED",
                "The user did not approve deletion. Do not ask again this run."
            )


        # Delete only after approval
        return self.tools.delete_product(product_id)
