import hashlib

from api.pagination import LimitPageNumberPagination
from django.db.models import F, Sum
from django.http import HttpResponse
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                     ShoppingCart, Tag)
from .serializers import (IngredientSerializer, RecipeMinifiedSerializer,
                          RecipeReadSerializer, RecipeWriteSerializer,
                          TagSerializer)


class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author_id == request.user.id


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None  # no pagination for tags
    lookup_field = "pk"


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny,)
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        if getattr(self, "action", None) == "list":
            name = self.request.query_params.get("name")
            if name:
                qs = qs.filter(name__istartswith=name)
        return qs


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

    REQUIRED_UPDATE_FIELDS = ("ingredients", "tags")

    def _require_update_fields(self, request):
        missing = [
            f for f in self.REQUIRED_UPDATE_FIELDS
            if f not in request.data]
        if missing:
            return Response(
                {f: ["This field is required."] for f in missing},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return None

    def update(self, request, *args, **kwargs):
        err = self._require_update_fields(request)
        if err:
            return err
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        err = self._require_update_fields(request)
        if err:
            return err
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(
        detail=True,
        methods=["post", "delete"],
        url_path="favorite",
        permission_classes=[permissions.IsAuthenticated],
    )
    def favorite(self, request, pk=None):
        recipe = self.get_object()
        if request.method.lower() == "post":
            obj, created = Favorite.objects.get_or_create(
                user=request.user, recipe=recipe
            )
            if not created:
                return Response(
                    {"detail": "Already in favorites."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                RecipeMinifiedSerializer(
                    recipe, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        deleted, _ = Favorite.objects.filter(
            user=request.user, recipe=recipe).delete()
        if not deleted:
            return Response(
                {"detail": "Recipe not in favorites."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["post", "delete"],
        url_path="shopping_cart",
        permission_classes=[permissions.IsAuthenticated],
    )
    def shopping_cart(self, request, pk=None):
        recipe = self.get_object()
        if request.method.lower() == "post":
            obj, created = ShoppingCart.objects.get_or_create(
                user=request.user, recipe=recipe
            )
            if not created:
                return Response(
                    {"detail": "Already in shopping cart."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            return Response(
                RecipeMinifiedSerializer(
                    recipe, context={"request": request}).data,
                status=status.HTTP_201_CREATED,
            )
        deleted, _ = ShoppingCart.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if not deleted:
            return Response(
                {"detail": "Recipe not in shopping cart."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=["get"],
        url_path="download_shopping_cart",
        permission_classes=[permissions.IsAuthenticated],
    )
    def download_shopping_cart(self, request):
        qs = (
            IngredientInRecipe.objects.filter(
                recipe__in_carts__user=request.user)
            .values(
                name=F("ingredient__name"),
                unit=F("ingredient__measurement_unit"))
            .annotate(total=Sum("amount"))
            .order_by("name")
        )

        lines = ["Shopping list"]
        for row in qs:
            lines.append(f"- {row['name']} ({row['unit']}): {row['total']}")
        content = "\n".join(
            lines) if len(lines) > 1 else "Shopping list is empty."

        response = HttpResponse(
            content, content_type="text/plain; charset=utf-8")
        response["Content-Disposition"] = (
            'attachment; filename="shopping_list.txt"')
        return response

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        author = params.get("author")
        if author:
            qs = qs.filter(author_id=author)

        tags = params.getlist("tags")
        if tags:
            qs = qs.filter(tags__slug__in=tags).distinct()

        user = self.request.user

        def as_bool(val):
            return str(val) == "1"

        is_fav = params.get("is_favorited")
        if is_fav in ("0", "1") and user.is_authenticated:
            qs = (
                qs.filter(favorited_by__user=user)
                if as_bool(is_fav)
                else qs.exclude(favorited_by__user=user)
            )

        is_cart = params.get("is_in_shopping_cart")
        if is_cart in ("0", "1") and user.is_authenticated:
            qs = (
                qs.filter(in_carts__user=user)
                if as_bool(is_cart)
                else qs.exclude(in_carts__user=user)
            )

        return qs

    @action(
        detail=True, methods=["get"],
        url_path="get-link", permission_classes=[AllowAny]
    )
    def get_link(self, request, pk=None):
        recipe = self.get_object()
        code = hashlib.sha1(str(recipe.id).encode()).hexdigest()[:3]
        host = request.build_absolute_uri("/").rstrip("/")
        return Response(
            {"short-link": f"{host}/s/{code}"}, status=status.HTTP_200_OK)
