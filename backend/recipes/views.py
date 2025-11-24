from django.http import Http404
from django.shortcuts import redirect
from recipes.models import Recipe


def shortlink_redirect(request, recipe_id):

    if not Recipe.objects.filter(pk=recipe_id).exists():
        raise Http404(f"Рецепт с id={recipe_id} не найден.")

    return redirect(f"/recipes/{recipe_id}/")
