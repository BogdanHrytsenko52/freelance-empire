"""Small Groq-compatible HTTP client with bounded retries and safe fallback signals."""

import json
import logging
import time
from dataclasses import dataclass
from typing import Protocol
from urllib import error, request

from django.conf import settings

logger = logging.getLogger(__name__)


class AiUnavailableError(RuntimeError):
    """A recoverable provider failure that callers should handle with fallback."""


class HttpTransport(Protocol):
    def send(self, payload: bytes, headers: dict[str, str], timeout: int) -> str: ...


class UrllibTransport:
    def send(self, payload: bytes, headers: dict[str, str], timeout: int) -> str:
        req = request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=payload,
            headers=headers,
            method="POST",
        )
        with request.urlopen(req, timeout=timeout) as response:
            return response.read().decode("utf-8")


@dataclass
class GroqClient:
    transport: HttpTransport | None = None

    def complete(self, *, system: str, user: str) -> str:
        if not settings.GROQ_ENABLED or not settings.GROQ_API_KEY:
            raise AiUnavailableError("AI provider is disabled or not configured.")
        payload = json.dumps(
            {
                "model": settings.GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": settings.GROQ_MAX_OUTPUT_TOKENS,
                "temperature": 0.2,
            }
        ).encode()
        transport = self.transport or UrllibTransport()
        headers = {
            "Authorization": f"Bearer {settings.GROQ_API_KEY}",
            "Content-Type": "application/json",
        }
        for attempt in range(settings.GROQ_MAX_RETRIES + 1):
            try:
                response = json.loads(
                    transport.send(payload, headers, settings.GROQ_TIMEOUT_SECONDS)
                )
                content = response["choices"][0]["message"]["content"]
                if not isinstance(content, str):
                    raise ValueError("missing content")
                return content
            except error.HTTPError as exc:
                if exc.code not in {429, 500, 502, 503, 504}:
                    raise AiUnavailableError(
                        "AI provider rejected the request."
                    ) from exc
            except (
                error.URLError,
                TimeoutError,
                ValueError,
                KeyError,
                IndexError,
                json.JSONDecodeError,
            ) as exc:
                logger.warning(
                    "AI provider request failed (%s); using bounded retry",
                    type(exc).__name__,
                )
            if attempt < settings.GROQ_MAX_RETRIES:
                time.sleep(0.2 * (2**attempt))
        raise AiUnavailableError("AI provider is unavailable.")
