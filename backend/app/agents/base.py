from abc import ABC, abstractmethod
from pydantic import BaseModel
from app.config import settings


class LLMResponse(BaseModel):
    text: str
    input_tokens: int
    output_tokens: int
    model_name: str


class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self, prompt: str, model: str, max_tokens: int = 2048
    ) -> LLMResponse:
        """Sends a completion request to the LLM provider.

        Args:
            prompt: The string prompt.
            model: The tier ("fast", "mid", "best") or direct model identifier.
            max_tokens: Maximum response tokens.

        Returns:
            LLMResponse: Text content plus input/output token usage.
        """
        pass


def get_provider() -> LLMProvider:
    """Factory function to get the current LLM Provider based on config."""
    from app.agents.providers import GroqProvider, OpenAIProvider

    provider_name = settings.LLM_PROVIDER.lower()
    if provider_name == "groq":
        return GroqProvider()
    elif provider_name == "openai":
        return OpenAIProvider()
    else:
        raise ValueError(f"Unsupported LLM provider: {provider_name}")
