from __future__ import annotations

from openai import OpenAI

from .base import AIProvider, ChatMessage, ChatResponse


class OpenAIProvider(AIProvider):
    """Works with any OpenAI-compatible API (OpenAI, Qwen DashScope, etc.)."""

    name = "openai"
    # Image-gen model used by `generate_image()`. Hard-coded for V1 since
    # only OpenAI proper exposes images.generate via the SDK reliably; Qwen
    # has its own endpoint (we intercept in QwenProvider below).
    image_model = "dall-e-3"

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

    def generate_image(self, *, prompt: str, size: str = "1024x1024") -> bytes:
        """Generate one image via the OpenAI Images API and return PNG bytes.

        Uses `b64_json` so we don't depend on the (1h-expiring) signed URL
        in the response — we own the bytes from here on. Caller is
        responsible for persisting + thumbnailing.
        """
        import base64
        if not prompt or not prompt.strip():
            raise ValueError("prompt is required")
        response = self._client.images.generate(
            model=self.image_model,
            prompt=prompt[:4000],
            size=size,
            n=1,
            response_format="b64_json",
        )
        data = response.data[0]
        if not data.b64_json:
            raise RuntimeError("Image API returned empty payload")
        return base64.b64decode(data.b64_json)


class QwenProvider(OpenAIProvider):
    """Alibaba DashScope OpenAI-compatible endpoint."""

    name = "qwen"
    DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def __init__(self, *, api_key: str, model: str, base_url: str = "") -> None:
        super().__init__(api_key=api_key, model=model, base_url=base_url or self.DEFAULT_BASE_URL)
