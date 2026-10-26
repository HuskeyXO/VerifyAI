
import os

from dotenv import load_dotenv

from app.services.ai.base import AIProvider
from app.services.ai.huggingface import HuggingFaceProvider
from app.services.ai.gemini import GeminiProvider
from app.services.ai.mock import MockAIProvider

load_dotenv()


class AIService:
    def __init__(self, provider: AIProvider):
        self.provider = provider

    def generate(self, prompt: str) -> str:
        return self.provider.generate(prompt)


def get_ai_service() -> AIService:
    provider_name = os.getenv(
        "AI_PROVIDER",
        "huggingface",
    ).strip().lower()

    if provider_name == "huggingface":
        provider = HuggingFaceProvider()
    elif provider_name == "gemini":
        provider = GeminiProvider()
    elif provider_name == "mock":
        provider = MockAIProvider()
    else:
        raise ValueError(
            f"Unsupported AI provider: {provider_name}"
        )

    return AIService(provider)
