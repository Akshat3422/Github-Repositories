import logging
from app.agents.base import LLMProvider, LLMResponse
from app.config import settings
from groq import AsyncGroq

logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    def __init__(self):
        # Allow running without key if not initialized yet
        self.api_key = settings.GROQ_API_KEY
        if self.api_key:
            self.client = AsyncGroq(api_key=self.api_key)
        else:
            self.client = None

    def _map_model(self, model_tier: str) -> str:
        mapping = {
            "fast": "llama-3.1-8b-instant",
            "mid": "llama-3.3-70b-versatile",
            "best": "llama-3.3-70b-versatile",
        }
        return mapping.get(model_tier.lower(), model_tier)

    async def complete(
        self, prompt: str, model: str, max_tokens: int = 2048
    ) -> LLMResponse:
        model_name = self._map_model(model)

        if not self.client:
            # Fallback for development if API key is not configured
            logger.warning(
                f"Groq API Key not configured. Using fallback stub response for model {model_name}."
            )
            return LLMResponse(
                text=f"[STUB GROQ] Response for model {model_name}. Please configure GROQ_API_KEY.\nPrompt summary: {prompt[:100]}...",
                input_tokens=10,
                output_tokens=15,
                model_name=model_name,
            )

        try:
            response = await self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model_name,
                max_tokens=max_tokens,
                temperature=0.7,
            )

            # Extract text content
            text = response.choices[0].message.content or ""

            # Extract usage details
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

            return LLMResponse(
                text=text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model_name=model_name,
            )
        except Exception as e:
            logger.error(f"Groq API request failed: {e}")
            raise


class OpenAIProvider(LLMProvider):
    async def complete(
        self, prompt: str, model: str, max_tokens: int = 2048
    ) -> LLMResponse:
        # Stub implementation as requested
        model_name = {"fast": "gpt-4o-mini", "mid": "gpt-4o", "best": "gpt-4o"}.get(
            model.lower(), model
        )

        logger.info(f"OpenAIProvider stub complete called with model: {model_name}")
        return LLMResponse(
            text=f"[STUB OPENAI] Completed request using {model_name} for prompt:\n{prompt[:60]}...",
            input_tokens=25,
            output_tokens=40,
            model_name=model_name,
        )
