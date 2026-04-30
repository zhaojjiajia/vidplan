from __future__ import annotations

from django.conf import settings

from .providers.base import AIProvider
from .providers.openai_provider import OpenAIProvider, QwenProvider

PROVIDER_CLASSES: dict[str, type[AIProvider]] = {
    "openai": OpenAIProvider,
    "qwen": QwenProvider,
}


def build_provider(*, name: str, api_key: str, model: str, base_url: str = "") -> AIProvider:
    cls = PROVIDER_CLASSES.get(name)
    if cls is None:
        raise ValueError(f"Unknown AI provider: {name}")
    return cls(api_key=api_key, model=model, base_url=base_url)


def resolve_provider_for_user(user) -> AIProvider:
    """Build an AI provider using the user's saved settings, falling back to env defaults."""
    from .models import UserAISetting

    setting = UserAISetting.objects.filter(user=user).first()
    if setting and setting.api_key:
        return build_provider(
            name=setting.provider,
            api_key=setting.api_key,
            model=setting.resolved_model(),
            base_url=setting.resolved_base_url(),
        )
    return build_provider(
        name=settings.AI_DEFAULT_PROVIDER,
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        base_url=settings.OPENAI_BASE_URL,
    )
