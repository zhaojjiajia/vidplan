from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel, UUIDModel


class AssetBase(UUIDModel, TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    name = models.CharField(max_length=120)
    payload = models.JSONField(default=dict, blank=True)
    fixed_traits = models.JSONField(default=list, blank=True)
    # Reference image gallery. Each entry is a dict produced by the
    # /assets/upload-image/ endpoint:
    #   {url, thumb_url, label, kind, width, height, size, uploaded_at}
    # `kind` is the canonical English key (front/side/back/...) — it routes
    # AI consumption later. `label` is the user-visible Chinese tag.
    images = models.JSONField(default=list, blank=True)

    class Meta:
        abstract = True
        ordering = ("-updated_at",)


class CharacterAsset(AssetBase):
    pass


class StyleAsset(AssetBase):
    pass


class WorldviewAsset(AssetBase):
    pass


class ColumnAsset(AssetBase):
    pass


class CustomAssetKind(UUIDModel, TimestampedModel):
    """User-defined asset category (e.g. "BGM 音乐", "常用道具").

    Lives alongside the four built-in tables. Each user has their own private
    set; we don't share kinds across accounts (would invite naming collisions
    and trust issues with schemas). `schema` drives the dynamic form that
    renders for assets of this kind on the frontend.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="custom_asset_kinds",
    )
    # Slug-style key (e.g. "bgm"). Used in URL paths so it must be safe.
    name = models.SlugField(max_length=64)
    label = models.CharField(max_length=64)
    icon = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    # List of {key, label, kind: 'text'|'textarea'|'lines', placeholder?}
    schema = models.JSONField(default=list, blank=True)
    # List of allowed image-tag strings, e.g. ["封面", "波形图", "其他"]
    image_labels = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(fields=("user", "name"), name="unique_kind_name_per_user"),
        ]

    def __str__(self) -> str:
        return f"{self.label} ({self.name})"


class CustomAsset(AssetBase):
    kind = models.ForeignKey(
        CustomAssetKind,
        on_delete=models.CASCADE,
        related_name="assets",
    )
