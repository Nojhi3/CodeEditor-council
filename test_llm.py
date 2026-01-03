from models.llm import LocalLLM, LLMError

def run_test():
    print("Initializing LocalLLM...")
    
    # 1. Setup
    # Ensure 'codellama:latest' is actually pulled in Ollama!
    llm = LocalLLM(model="codellama:latest", temperature=0.1)

    # 2. Define the Test Case
    system_role = "You are a senior Java developer. You answer ONLY with code. No explanations."
    user_task = "Write a method to check if a string is a palindrome."

    print(f"\nModel: {llm.model}")
    print(f"Task: {user_task}")
    print("-" * 30)

    # 3. Execution
    try:
        result = llm.generate(prompt=user_task, system_prompt=system_role)
        
        print("\n--- Model Output ---")
        print(result)
        print("--------------------")
        
    except LLMError as e:
        print(f"\n[ERROR] Test Failed: {e}")
        print("Tip: Run 'ollama list' in terminal to check your models.")

if __name__ == "__main__":
    run_test()