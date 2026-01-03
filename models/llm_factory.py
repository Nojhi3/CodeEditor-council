# models/llm_factory.py
from models.local_llm import LocalLLM
# later:
# from models.gemini_llm import GeminiLLM


def get_llm(provider: str = "local"):
    if provider == "local":
        return LocalLLM()

    # elif provider == "gemini":
    #     return GeminiLLM()

    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
