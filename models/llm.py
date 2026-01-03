import requests
from typing import Optional

class LLMError(Exception):
    """Custom exception for LLM failures."""
    pass

class LocalLLM:
    """
    Interface for a locally running Ollama instance.
    """

    def __init__(
        self,
        # CHANGED: Use the native Ollama endpoint, not the OpenAI-compat one
        base_url: str = "http://localhost:11434/api/generate",
        model: str = "codellama:latest",  # Default to the model you have installed
        temperature: float = 0.2,
        timeout: int = 60,
    ):
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Sends a prompt to the local model.
        
        Args:
            prompt: The specific task or code request.
            system_prompt: (Optional) The persona or rules for the model.
        """
        
        # CHANGED: Native Ollama API supports a separate 'system' field.
        # This works better than concatenating strings manually.
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature
            }
        }

        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = requests.post(
                self.base_url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()

            data = response.json()
            
            # Ollama native API returns the text in the 'response' key
            return data.get("response", "").strip()

        except requests.exceptions.ConnectionError:
            raise LLMError(
                f"Could not connect to Ollama at {self.base_url}. Is the server running?"
            )
        except requests.exceptions.RequestException as e:
            raise LLMError(f"LLM request failed: {str(e)}")
        except Exception as e:
            raise LLMError(f"Unexpected error: {str(e)}")