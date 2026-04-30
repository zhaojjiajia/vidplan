from rest_framework.renderers import BaseRenderer


class MarkdownRenderer(BaseRenderer):
    media_type = "text/markdown"
    format = "md"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        if isinstance(data, str):
            return data.encode(self.charset)
        # action returns HttpResponse directly, so DRF won't actually call this on the body.
        return str(data).encode(self.charset)
