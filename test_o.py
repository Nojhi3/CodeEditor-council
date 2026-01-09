from core.orchestrator import Orchestrator

orchestrator = Orchestrator(provider="local")

response = orchestrator.run(
    "Generate the Fibonacci sequence up to n and save it to a file."
)

print("\n=== RESPONSE ===\n")
print(response)
