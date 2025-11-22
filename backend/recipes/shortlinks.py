from django.shortcuts import redirect
from django.http import JsonResponse
from rest_framework import status

from recipes.models import Recipe

def shortlink_redirect(request, recipe_id):

    if not Recipe.objects.filter(pk=recipe_id).exists():
        return JsonResponse(
            {"detail": "Ссылка не найдена."},
            status=status.HTTP_404_NOT_FOUND
        )

    return redirect(f"/recipes/{recipe_id}/")
