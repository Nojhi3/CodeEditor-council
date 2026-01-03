from core.orchestrator import Orchestrator

orchestrator = Orchestrator(provider="local")

response = orchestrator.run(
    "Write a Python function that takes a list of numbers and returns the list sorted in ascending order. Save the code to a file named 'sort_numbers.py'."
)

print("\n=== RESPONSE ===\n")
print(response)
