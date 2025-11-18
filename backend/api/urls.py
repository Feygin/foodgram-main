from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import ShortLinkRedirectView

from .views import (
    UsersViewSet, TagViewSet, IngredientViewSet, RecipeViewSet
)

router = DefaultRouter()
router.register("users", UsersViewSet, basename="users")
router.register("tags", TagViewSet, basename="tags")
router.register("ingredients", IngredientViewSet, basename="ingredients")
router.register("recipes", RecipeViewSet, basename="recipes")

urlpatterns = [
    path("auth/", include("djoser.urls.authtoken")),
    path("s/<str:code>/", ShortLinkRedirectView.as_view(), name="short-link"),
    path("", include(router.urls)),
]
