import google.genai as genai
from models.base import BaseLLM
from dotenv import load_dotenv
load_dotenv()

import os

class GeminiLLM(BaseLLM):
    def __init__(self, model="gemini-1.5-pro"):
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel(model)

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        prompt = f"{system_prompt}\n\n{user_prompt}"
        response = self.model.generate_content(prompt)
        return response.text
