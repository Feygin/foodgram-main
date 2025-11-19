from io import BytesIO

from django.db.models import F, Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, Tag)
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from api.filters import IngredientFilter, RecipeFilter
from api.pagination import LimitPageNumberPagination
from api.report import render_shopping_list
from api.serializers import (IngredientSerializer, RecipeMinifiedSerializer,
                             RecipeReadSerializer, RecipeWriteSerializer,
                             TagSerializer)
from .shortlinks import encode_id


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            request.method in permissions.SAFE_METHODS
            or obj.author_id == request.user.id
        )


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    pagination_class = None

    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = (
        Recipe.objects.all()
        .select_related("author")
        .prefetch_related("tags", "recipe_ingredients__ingredient")
    )
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly,
    )
    pagination_class = LimitPageNumberPagination

    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def _process_relation(self, request, model, pk):
        messages = {
            Favorite: 'Рецепт "{name}" уже в избранном.',
            ShoppingCart: 'Рецепт "{name}" уже в списке покупок.',
        }

        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == "DELETE":
            obj = model.objects.filter(user=request.user, recipe=recipe)
            if not obj.exists():
                return Response(
                    {"detail": "Рецепта нет в этом списке."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        _, created = model.objects.get_or_create(
            user=request.user, recipe=recipe)

        if not created:
            return Response(
                {"detail": messages[model].format(name=recipe.name)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            RecipeMinifiedSerializer(
                recipe, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post", "delete"], url_path="favorite")
    def favorite(self, request, pk=None):
        return self._process_relation(request, Favorite, pk)

    @action(detail=True, methods=["post", "delete"], url_path="shopping_cart")
    def shopping_cart(self, request, pk=None):
        return self._process_relation(request, ShoppingCart, pk)

    @action(detail=False, methods=["get"], url_path="download_shopping_cart")
    def download_shopping_cart(self, request):
        products = (
            IngredientInRecipe.objects
            .filter(recipe__shopping_cart__user=request.user)
            .values(
                name=F("ingredient__name"),
                unit=F("ingredient__measurement_unit")
            )
            .annotate(total=Sum("amount"))
            .order_by("name")
        )

        recipes = (
            Recipe.objects.filter(shopping_cart__user=request.user)
            .select_related("author")
            .order_by("name")
        )

        text = render_shopping_list(products, recipes)
        buffer = BytesIO(text.encode("utf-8"))
        return FileResponse(
            buffer,
            as_attachment=True,
            filename="shopping_list.txt"
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="get-link",
        permission_classes=[AllowAny],
    )
    def get_link(self, request, pk=None):
        code = encode_id(int(pk))

        short_url = request.build_absolute_uri(
            reverse("short-link", kwargs={"code": code})
        )

        return Response({"short-link": short_url})
