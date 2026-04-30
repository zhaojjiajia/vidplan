from django.conf import settings
from django.db import models

from apps.core.models import TimestampedModel, UUIDModel


class AssetBase(UUIDModel, TimestampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    name = models.CharField(max_length=120)
    payload = models.JSONField(default=dict, blank=True)
    fixed_traits = models.JSONField(default=list, blank=True)

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
