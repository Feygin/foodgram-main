import string

from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from rest_framework.response import Response
from rest_framework.views import APIView

from recipes.models import Recipe

_ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase
_BASE = len(_ALPHABET)


def encode_id(num: int) -> str:
    if num <= 0:
        return "0"
    chars = []
    while num > 0:
        num, rem = divmod(num, _BASE)
        chars.append(_ALPHABET[rem])
    return "".join(reversed(chars))


def decode_code(code: str) -> int:
    num = 0
    for ch in code:
        if ch not in _ALPHABET:
            raise ValueError("invalid code")
        num = num * _BASE + _ALPHABET.index(ch)
    return num


class ShortLinkRedirectView(APIView):
    def get(self, request, code):
        try:
            recipe_id = decode_code(code)
        except ValueError:
            return Response({"detail": "Ссылка не найдена."}, status=404)

        recipe = get_object_or_404(Recipe, pk=recipe_id)
        url = reverse("recipe-detail", args=[recipe.id])
        return redirect(url)
