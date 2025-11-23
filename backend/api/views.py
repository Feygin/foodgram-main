from django.contrib.auth import get_user_model
from django.db.models import F, Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from api.filters import IngredientFilter, RecipeFilter
from api.pagination import LimitPageNumberPagination
from api.report import render_shopping_list
from api.serializers import (
    AvatarSerializer,
    IngredientSerializer,
    RecipeMinifiedSerializer,
    RecipeReadSerializer,
    RecipeWriteSerializer,
    TagSerializer,
    UserSerializer,
    UserWithRecipesSerializer,
)
from recipes.models import (
    Favorite,
    Ingredient,
    IngredientInRecipe,
    Recipe,
    ShoppingCart,
    Subscription,
    Tag,
)

User = get_user_model()


class UsersViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    pagination_class = LimitPageNumberPagination
    serializer_class = UserSerializer

    @action(detail=False, methods=["get"],
            permission_classes=[IsAuthenticated])
    def me(self, request, *args, **kwargs):
        return super().me(request, *args, **kwargs)

    @action(
        detail=False,
        methods=["put", "delete"],
        url_path="me/avatar",
        permission_classes=[permissions.IsAuthenticated],
    )
    def avatar(self, request):

        if request.method.lower() == "delete":
            if request.user.avatar:
                request.user.avatar.delete(save=False)
            request.user.avatar = None
            request.user.save(update_fields=["avatar"])
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = AvatarSerializer(
            instance=request.user,
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"avatar": request.build_absolute_uri(request.user.avatar.url)})

    @action(
        detail=False,
        methods=["get"],
        url_path="subscriptions",
        permission_classes=[permissions.IsAuthenticated],
    )
    def subscriptions(self, request):
        authors_qs = User.objects.filter(authors__user=request.user)
        page = self.paginate_queryset(authors_qs)
        serializer = UserWithRecipesSerializer(
            page, many=True, context={"request": request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=["post", "delete"],
        url_path="subscribe",
        permission_classes=[permissions.IsAuthenticated],
    )
    def subscribe(self, request, id=None):

        if request.method.lower() == "delete":
            get_object_or_404(
                Subscription, user=request.user, author_id=id).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # POST
        author = get_object_or_404(User, pk=id)

        if request.user == author:
            raise ValidationError(
                {"detail": "Нельзя подписаться на себя."})

        _, created = Subscription.objects.get_or_create(
            user=request.user, author_id=id)

        if not created:
            raise ValidationError(
                {"detail": f'Подписка на "{author.username}" уже существует.'}
            )

        return Response(
            UserWithRecipesSerializer(
                author, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


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
        if request.method == "DELETE":
            get_object_or_404(model, user=request.user, recipe_id=pk).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        recipe = get_object_or_404(Recipe, pk=pk)

        obj, created = model.objects.get_or_create(
            user=request.user, recipe=recipe)

        if not created:
            raise ValidationError(
                f'Рецепт "{recipe.name}" уже {model._meta.verbose_name}.'
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
            IngredientInRecipe.objects.filter(
                recipe__shopping_cart__user=request.user)
            .values(name=F("ingredient__name"),
                    unit=F("ingredient__measurement_unit"))
            .annotate(total=Sum("amount"))
            .order_by("name")
        )

        recipes = (
            Recipe.objects.filter(shopping_cart__user=request.user)
            .select_related("author")
            .order_by("name")
        )

        text = render_shopping_list(products, recipes)
        return FileResponse(
            text.encode("utf-8"),
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
        recipe = get_object_or_404(Recipe, pk=pk)
        short_url = request.build_absolute_uri(
            reverse("short-link", args=[recipe.pk]))
        return Response({"short-link": short_url})
