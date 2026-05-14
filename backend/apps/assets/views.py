from __future__ import annotations

import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from django.conf import settings
from PIL import Image, UnidentifiedImageError
from rest_framework import status, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.registry import resolve_provider_for_user
from apps.core.permissions import IsOwner

from .models import (
    CharacterAsset,
    ColumnAsset,
    CustomAsset,
    CustomAssetKind,
    StyleAsset,
    WorldviewAsset,
)
from .serializers import (
    CharacterAssetSerializer,
    ColumnAssetSerializer,
    CustomAssetKindSerializer,
    CustomAssetSerializer,
    StyleAssetSerializer,
    WorldviewAssetSerializer,
)


class _OwnedViewSet(viewsets.ModelViewSet):
    permission_classes = (IsOwner,)
    queryset = None
    serializer_class = None
    filter_backends = (SearchFilter, OrderingFilter)
    search_fields = ("name",)
    ordering_fields = ("name", "updated_at", "created_at")
    ordering = ("-updated_at",)

    def get_queryset(self):
        return self.queryset.model.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CharacterAssetViewSet(_OwnedViewSet):
    queryset = CharacterAsset.objects.all()
    serializer_class = CharacterAssetSerializer


class StyleAssetViewSet(_OwnedViewSet):
    queryset = StyleAsset.objects.all()
    serializer_class = StyleAssetSerializer


class WorldviewAssetViewSet(_OwnedViewSet):
    queryset = WorldviewAsset.objects.all()
    serializer_class = WorldviewAssetSerializer


class ColumnAssetViewSet(_OwnedViewSet):
    queryset = ColumnAsset.objects.all()
    serializer_class = ColumnAssetSerializer


class CustomAssetKindViewSet(_OwnedViewSet):
    queryset = CustomAssetKind.objects.all()
    serializer_class = CustomAssetKindSerializer
    search_fields = ("name", "label")


class CustomAssetViewSet(_OwnedViewSet):
    queryset = CustomAsset.objects.all()
    serializer_class = CustomAssetSerializer
    search_fields = ("name",)

    def get_queryset(self):
        qs = super().get_queryset()
        kind_id = self.request.query_params.get("kind")
        if kind_id:
            qs = qs.filter(kind_id=kind_id)
        return qs


# ---- Image upload ---------------------------------------------------------

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
THUMBNAIL_SIZE = (240, 240)


class AssetImageUploadView(APIView):
    """Upload a single asset reference image.

    Returns a small JSON descriptor the frontend can append to an asset's
    `images` array. We don't persist it as its own DB row — the source of
    truth is the JSONField on whichever asset model owns it.
    """

    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        upload = request.FILES.get("file")
        if upload is None:
            return Response({"detail": "缺少 file 字段"}, status=status.HTTP_400_BAD_REQUEST)

        if upload.size > MAX_IMAGE_SIZE_BYTES:
            return Response(
                {"detail": f"图片超出 5 MB 限制 (实际 {upload.size // 1024} KB)"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        suffix = Path(upload.name or "").suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            return Response(
                {"detail": f"暂不支持的图片格式: {suffix or '(未知)'},仅支持 JPG/PNG/WebP"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = upload.read()
            image = Image.open(BytesIO(data))
            image.load()  # force PIL to parse, catches truncated files
        except (UnidentifiedImageError, OSError) as exc:
            return Response(
                {"detail": f"无法识别为图片: {exc}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if image.format not in ALLOWED_IMAGE_FORMATS:
            return Response(
                {"detail": f"图片格式 {image.format} 不在白名单"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Layout: media/assets/<user_id>/<uuid4>/<original> + <thumb>.jpg
        # Per-image folder so thumb file lives alongside its source — easier
        # to clean up later if we add a delete endpoint.
        media_root = Path(settings.MEDIA_ROOT)
        relative_dir = Path("assets") / str(request.user.id) / uuid.uuid4().hex
        target_dir = media_root / relative_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        full_name = f"original{suffix}"
        thumb_name = "thumb.jpg"
        full_path = target_dir / full_name
        thumb_path = target_dir / thumb_name

        full_path.write_bytes(data)

        # Build thumbnail. Convert to RGB to drop alpha (JPEG can't carry it)
        # and to normalize palette/RGBA inputs into a uniform thumb format.
        thumb = image.copy()
        if thumb.mode != "RGB":
            thumb = thumb.convert("RGB")
        thumb.thumbnail(THUMBNAIL_SIZE)
        thumb.save(thumb_path, format="JPEG", quality=80, optimize=True)

        media_url = settings.MEDIA_URL.rstrip("/") + "/"
        return Response(
            {
                "url": f"{media_url}{relative_dir}/{full_name}",
                "thumb_url": f"{media_url}{relative_dir}/{thumb_name}",
                "width": image.width,
                "height": image.height,
                "size": upload.size,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


ALLOWED_IMAGE_SIZES = {"1024x1024", "1792x1024", "1024x1792"}


class AssetAIImageGenerateView(APIView):
    """Ask the user's configured AI provider to generate a reference image
    from a text prompt. Persists the result to MEDIA_ROOT (same shape as
    upload-image) so the URL is stable and not subject to vendor link expiry.
    """

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        prompt = (request.data.get("prompt") or "").strip()
        size = request.data.get("size") or "1024x1024"
        if not prompt:
            return Response({"detail": "请填写描述"}, status=status.HTTP_400_BAD_REQUEST)
        if size not in ALLOWED_IMAGE_SIZES:
            return Response(
                {"detail": f"不支持的尺寸 {size},仅支持 {', '.join(sorted(ALLOWED_IMAGE_SIZES))}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        provider = resolve_provider_for_user(request.user)
        if not hasattr(provider, "generate_image"):
            return Response(
                {"detail": "当前 AI 提供商不支持图片生成,请在 AI 设置切到 OpenAI"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            png_bytes = provider.generate_image(prompt=prompt, size=size)
        except Exception as exc:  # noqa: BLE001 — surface upstream error
            return Response(
                {"detail": f"AI 生成失败: {type(exc).__name__}: {str(exc)[:300]}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Same disk layout as upload-image so cleanup/serving paths stay uniform.
        media_root = Path(settings.MEDIA_ROOT)
        relative_dir = Path("assets") / str(request.user.id) / uuid.uuid4().hex
        target_dir = media_root / relative_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        full_name = "ai.png"
        thumb_name = "thumb.jpg"
        full_path = target_dir / full_name
        thumb_path = target_dir / thumb_name

        full_path.write_bytes(png_bytes)
        image = Image.open(BytesIO(png_bytes))
        thumb = image.copy()
        if thumb.mode != "RGB":
            thumb = thumb.convert("RGB")
        thumb.thumbnail(THUMBNAIL_SIZE)
        thumb.save(thumb_path, format="JPEG", quality=80, optimize=True)

        media_url = settings.MEDIA_URL.rstrip("/") + "/"
        return Response(
            {
                "url": f"{media_url}{relative_dir}/{full_name}",
                "thumb_url": f"{media_url}{relative_dir}/{thumb_name}",
                "width": image.width,
                "height": image.height,
                "size": len(png_bytes),
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                "ai_generated": True,
                "prompt": prompt,
            },
            status=status.HTTP_201_CREATED,
        )
