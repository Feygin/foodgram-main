from django.urls import path

from recipes.views import shortlink_redirect

urlpatterns = [
    path("<int:recipe_id>", shortlink_redirect, name="short-link"),
]
