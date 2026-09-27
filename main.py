from agent import ShoppingAgent
from schemas import Role


def choose_role():
    print("\nSelect role:")
    print("1. Customer")
    print("2. Admin")

    choice = input("> ").strip()

    if choice == "2":
        return Role.ADMIN

    return Role.CUSTOMER


def main():
    print("=" * 40)
    print("Safe Shopping Agent")
    print("=" * 40)

    role = choose_role()

    print(f"\nRole: {role.value}")

    agent = ShoppingAgent(role)

    ready, message = agent.startup_check()

    if not ready:
        print(f"Startup error: {message}")
        return

    print(message)
    print("Type 'quit' to stop.")

    while True:
        request = input("\nYou> ").strip()

        if request.lower() in ["quit", "exit"]:
            print("Goodbye.")
            break

        if not request:
            print("Please enter a request.")
            continue

        answer = agent.run(request)

        print(f"\nAssistant> {answer}")


if __name__ == "__main__":
    main()
