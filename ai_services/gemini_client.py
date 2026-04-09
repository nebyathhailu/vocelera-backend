import logging
from typing import Optional

from google import genai
from django.conf import settings
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)


def _get_client() -> genai.Client:
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _get_generation_config() -> dict:
    return {
        "temperature": settings.GEMINI_TEMPERATURE,
        "max_output_tokens": settings.GEMINI_MAX_TOKENS,
        "top_p": 0.95,
        "top_k": 64,
    }


def _is_retryable(exc: BaseException) -> bool:
    """Only retry on transient errors, never on quota/auth errors."""
    if isinstance(exc, GeminiClientError):
        return False

    # Check for quota errors without importing at top level
    exc_str = str(exc).upper()
    if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
        logger.warning("Gemini quota/rate limit hit (429 RESOURCE_EXHAUSTED)")
        return False

    # Also catch common non-retryable auth/permission errors
    if any(code in exc_str for code in ["401", "403", "UNAUTHENTICATED", "PERMISSION_DENIED"]):
        return False

    return True


class GeminiClient:

    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    def generate(prompt: str, system_instruction: Optional[str] = None) -> str:
        try:
            client = _get_client()

            full_prompt = (
                f"{system_instruction}\n\n{prompt}"
                if system_instruction
                else prompt
            )

            logger.info(
                "Sending prompt to Gemini [model=%s, prompt_length=%d]",
                settings.GEMINI_MODEL,
                len(full_prompt),
            )

            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=full_prompt,
                config=_get_generation_config(),
            )

            text = getattr(response, "text", None)

            # fallback for candidates structure
            if not text and hasattr(response, "candidates"):
                try:
                    text = response.candidates[0].content.parts[0].text
                except Exception:
                    text = None

            if not text:
                raise GeminiClientError("Empty response received from Gemini.")

            logger.info("Gemini response received [length=%d]", len(text))
            return text.strip()

        except GeminiClientError:
            raise
        except Exception as exc:
            # Re-raise quota errors cleanly
            if "429" in str(exc) or "RESOURCE_EXHAUSTED" in str(exc).upper():
                logger.warning("Gemini quota exceeded")
                raise
            logger.exception("Gemini API call failed: %s", exc)
            raise GeminiClientError(f"Gemini call failed: {exc}") from exc

    @staticmethod
    def generate_structured(prompt: str, system_instruction: Optional[str] = None) -> dict:
        from ai_services.response_parser import safe_parse_json

        raw = GeminiClient.generate(prompt, system_instruction)
        return safe_parse_json(raw)


class GeminiClientError(Exception):
    pass