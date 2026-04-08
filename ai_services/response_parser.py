import json
import re
import logging

logger = logging.getLogger(__name__)


def safe_parse_json(raw_text: str) -> dict:
    """
    Safely extract and parse JSON from a Gemini response.

    Gemini sometimes wraps JSON in markdown code blocks — this handles that.

    Args:
        raw_text: Raw string response from Gemini.

    Returns:
        dict: Parsed JSON content.

    Raises:
        ValueError: If JSON cannot be extracted.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"```(?:json)?\s*", "", raw_text).strip().rstrip("`").strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Gemini JSON response: %s\nRaw: %s", e, raw_text[:500])
        raise ValueError(f"Could not parse Gemini response as JSON: {e}") from e


def extract_text_response(raw_text: str) -> str:
    """
    Clean and return plain text from a Gemini response.

    Args:
        raw_text: Raw string response from Gemini.

    Returns:
        str: Cleaned text.
    """
    return raw_text.strip()