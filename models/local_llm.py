import requests
from models.base import BaseLLM


class LocalLLM(BaseLLM):
    def __init__(self, model: str = "codellama:latest", url: str = "http://localhost:11434/api/generate"):
        """
        Initializes the Local LLM client.
        
        Args:
            model (str): The name of the model to use (e.g., 'llama3', 'codellama').
            url (str): The full endpoint URL for the Ollama API.
        """
        self.model = model
        self.url = url

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False,
        }

        r = requests.post(self.url, json=payload)
        r.raise_for_status()
        return r.json()["response"]
