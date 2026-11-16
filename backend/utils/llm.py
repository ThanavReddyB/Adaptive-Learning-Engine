import json
import re
import time
from typing import Any

from openai import APIError, APITimeoutError, OpenAI, RateLimitError

from utils.config import DEFAULT_MODEL, LLM_MAX_RETRIES, LLM_TIMEOUT, OPENROUTER_BASE_URL, OR_KEY

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=OR_KEY,
            base_url=OPENROUTER_BASE_URL,
        )
    return _client


def _extract_json(raw: str) -> str:
    """Strip markdown code fences and isolate the first JSON object or array."""
    raw = raw.strip()
    # Remove ```json ... ``` or ``` ... ```
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    raw = raw.strip()

    # If it contains extra prose before the JSON, find the first { or [
    match = re.search(r"(\{|\[)", raw)
    if match:
        start = match.start()
        raw = raw[start:]

    return raw


def call_llm(
    system_prompt: str,
    user_message: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.3,
    timeout: int = LLM_TIMEOUT,
    max_retries: int = LLM_MAX_RETRIES,
) -> str:
    client = get_client()
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=temperature,
                timeout=timeout,
            )
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("LLM returned empty content")
            return content
        except (RateLimitError, APITimeoutError) as e:
            last_error = e
            wait = 2 ** attempt
            time.sleep(wait)
        except APIError as e:
            last_error = e
            if attempt == max_retries - 1:
                break
            time.sleep(2 ** attempt)

    raise RuntimeError(f"LLM call failed after {max_retries} attempts: {last_error}")


def call_llm_json(
    system_prompt: str,
    user_message: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.1,
    timeout: int = LLM_TIMEOUT,
    max_retries: int = LLM_MAX_RETRIES,
) -> Any:
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            raw = call_llm(
                system_prompt,
                user_message,
                model=model,
                temperature=temperature,
                timeout=timeout,
                max_retries=1,  # inner retry handled here
            )
            cleaned = _extract_json(raw)
            return json.loads(cleaned)
        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            # Append explicit correction request on retry
            user_message = (
                user_message
                + "\n\nIMPORTANT: Your previous response could not be parsed as JSON. "
                "Return ONLY a valid JSON object or array with NO additional text."
            )
            time.sleep(1)
        except RuntimeError as e:
            last_error = e
            time.sleep(2 ** attempt)

    raise ValueError(
        f"Failed to obtain valid JSON from LLM after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
