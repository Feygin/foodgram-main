import base64
import imghdr
import uuid

from django.core.files.base import ContentFile
from rest_framework import serializers


class Base64ImageField(serializers.ImageField):

    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith("data:image"):
            header, b64data = data.split(";base64,")
            data = b64data

        if isinstance(data, str):
            try:
                decoded = base64.b64decode(data)
            except Exception:
                raise serializers.ValidationError("Invalid base64 image.")

            ext = imghdr.what(None, decoded) or "jpg"
            file_name = f"{uuid.uuid4().hex}.{ext}"
            data = ContentFile(decoded, name=file_name)

        return super().to_internal_value(data)
