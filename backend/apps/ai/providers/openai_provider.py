from __future__ import annotations

from openai import OpenAI

from .base import AIProvider, ChatMessage, ChatResponse


class OpenAIProvider(AIProvider):
    """Works with any OpenAI-compatible API (OpenAI, Qwen DashScope, etc.)."""

    name = "openai"

    def __init__(self, *, api_key: str, model: str, base_url: str = "", timeout: float = 180.0) -> None:
        if not api_key:
            raise ValueError("AI provider api_key is required")
        kwargs: dict = {"api_key": api_key, "timeout": timeout}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)
        self._default_model = model

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
        params: dict = {
            "model": model or self._default_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
        }
        if max_tokens:
            params["max_tokens"] = max_tokens
        if response_format == "json":
            params["response_format"] = {"type": "json_object"}
        if timeout is not None:
            params["timeout"] = timeout

        completion = self._client.chat.completions.create(**params)
        choice = completion.choices[0]
        usage = completion.usage
        return ChatResponse(
            content=choice.message.content or "",
            model=completion.model,
            usage={
                "input_tokens": getattr(usage, "prompt_tokens", 0) if usage else 0,
                "output_tokens": getattr(usage, "completion_tokens", 0) if usage else 0,
            },
            raw=completion,
        )


class QwenProvider(OpenAIProvider):
    """Alibaba DashScope OpenAI-compatible endpoint."""

    name = "qwen"
    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def __init__(self, *, api_key: str, model: str, base_url: str = "") -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url or self.DEFAULT_BASE_URL)
