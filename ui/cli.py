# ui/cli.py
from core.orchestrator import Orchestrator


def start_cli():
    orchestrator = Orchestrator()

    print("🧠 CodeEditor AI (type 'exit' to quit)\n")

    while True:
        user_input = input("> ")

        if user_input.lower() in {"exit", "quit"}:
            break

        response = orchestrator.run(user_input)
        print("\n" + response + "\n")
