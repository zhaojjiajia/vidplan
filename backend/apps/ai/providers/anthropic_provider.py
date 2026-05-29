from __future__ import annotations

import json
from urllib import error, request

from .base import AIProvider, ChatMessage, ChatResponse


class AnthropicProvider(AIProvider):
    name = "anthropic"
    DEFAULT_BASE_URL = "https://api.anthropic.com"
    DEFAULT_MAX_TOKENS = 4096

    def __init__(self, *, api_key: str, model: str, base_url: str = "", timeout: float = 180.0) -> None:
        if not api_key:
            raise ValueError("AI provider api_key is required")
        self._api_key = api_key
        self._default_model = model
        self._base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self._timeout = timeout

    def _messages_url(self) -> str:
        if self._base_url.endswith("/v1/messages"):
            return self._base_url
        if self._base_url.endswith("/v1"):
            return f"{self._base_url}/messages"
        return f"{self._base_url}/v1/messages"

    def _split_messages(self, messages: list[ChatMessage]) -> tuple[str, list[dict[str, str]]]:
        system_parts: list[str] = []
        anthropic_messages: list[dict[str, str]] = []

        for message in messages:
            if message.role == "system":
                system_parts.append(message.content)
            elif message.role in {"user", "assistant"}:
                anthropic_messages.append({"role": message.role, "content": message.content})
            else:
                anthropic_messages.append({"role": "user", "content": message.content})

        if not anthropic_messages:
            anthropic_messages.append({"role": "user", "content": ""})

        return "\n\n".join(system_parts), anthropic_messages

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        response_format: str = "text",
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> ChatResponse:
        system, anthropic_messages = self._split_messages(messages)
        request_model = model or self._default_model
        payload: dict = {
            "model": request_model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens or self.DEFAULT_MAX_TOKENS,
        }
        if system:
            payload["system"] = system

        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self._messages_url(),
            data=body,
            method="POST",
            headers={
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
                "x-api-key": self._api_key,
            },
        )

        try:
            with request.urlopen(req, timeout=timeout or self._timeout) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic API error {exc.code}: {err_body[:500]}") from exc
        except error.URLError as exc:
            raise RuntimeError(f"Anthropic API connection error: {exc.reason}") from exc

        content = "".join(
            part.get("text", "")
            for part in raw.get("content", [])
            if isinstance(part, dict) and part.get("text")
        )
        usage = raw.get("usage") or {}
        return ChatResponse(
            content=content,
            model=raw.get("model") or request_model,
            usage={
                "input_tokens": int(usage.get("input_tokens") or 0),
                "output_tokens": int(usage.get("output_tokens") or 0),
            },
            raw=raw,
        )
