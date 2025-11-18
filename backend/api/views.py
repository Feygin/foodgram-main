import string

from .pagination import LimitPageNumberPagination
from django.contrib.auth import get_user_model
from django.db.models import F, Sum
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from djoser.serializers import UserCreateSerializer
from djoser.views import UserViewSet as DjoserUserViewSet
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.filters import SearchFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from io import BytesIO
from django.http import Http404
from .filters import RecipeFilter, IngredientFilter

from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                     ShoppingCart, Subscription, Tag)
from .report import render_shopping_list
from .serializers import (AvatarSerializer, IngredientSerializer,
                          RecipeMinifiedSerializer, RecipeReadSerializer,
                          RecipeWriteSerializer, TagSerializer, UserSerializer,
                          UserWithRecipesSerializer)

User = get_user_model()

# ---------------------------------------------------------
#   Вспомогательные функции для коротких ссылок
# ---------------------------------------------------------

_ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase
_BASE = len(_ALPHABET)


def encode_id(num: int) -> str:
    """Переводим целое число в base-62 строку."""
    if num <= 0:
        return "0"
    chars = []
    while num > 0:
        num, rem = divmod(num, _BASE)
        chars.append(_ALPHABET[rem])
    return "".join(reversed(chars))


def decode_code(code: str) -> int:
    """Переводим base-62 строку обратно в целое число."""
    num = 0
    for ch in code:
        if ch not in _ALPHABET:
            raise ValueError("invalid code")
        num = num * _BASE + _ALPHABET.index(ch)
    return num

class UsersViewSet(DjoserUserViewSet):
    """
    Пользовательские viewset на базе Djoser.
    Удалены лишние методы (list/get_permissions/get_serializer_class/set_password).
    Добавлены только то, чего нет у Djoser: аватар, список подписок, подписка/отписка.
    """
    queryset = User.objects.all()
    pagination_class = LimitPageNumberPagination
    serializer_class = UserSerializer  # базовый сериализатор для list/retrieve

    # По требованию ревьюера: perform-версия create
    def perform_create(self, serializer: UserCreateSerializer):
        serializer.save()

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request, *args, **kwargs):
        """Запрещаем доступ анонимам. Djoser-код полностью переиспользуем."""
        return super().me(request, *args, **kwargs)

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar', permission_classes=[permissions.IsAuthenticated])
    def avatar(self, request):
        # ранний возврат для DELETE
        if request.method.lower() == 'delete':
            if request.user.avatar:
                request.user.avatar.delete(save=False)
            request.user.avatar = None
            request.user.save(update_fields=['avatar'])
            return Response(status=status.HTTP_204_NO_CONTENT)

        # PUT
        serializer = AvatarSerializer(instance=request.user, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'avatar': request.build_absolute_uri(request.user.avatar.url)})

    @action(detail=False, methods=['get'], url_path='subscriptions', permission_classes=[permissions.IsAuthenticated])
    def subscriptions(self, request):
        # Все авторы, на которых подписан текущий пользователь
        authors_qs = User.objects.filter(authors__user=request.user)
        page = self.paginate_queryset(authors_qs)
        serializer = UserWithRecipesSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='subscribe',
        permission_classes=[permissions.IsAuthenticated]
    )
    def subscribe(self, request, *args, **kwargs):
        # Получаем ID автора, учитывая lookup_field="id" у Djoser
        author_id = kwargs.get(self.lookup_field)

        # Проверка существования автора
        author = get_object_or_404(User, pk=author_id)

        # DELETE — отписка
        if request.method.lower() == 'delete':
            try:
                get_object_or_404(Subscription, user=request.user, author_id=author_id).delete()
            except Http404:
                return Response(
                    {"detail": "Вы не подписаны на этого пользователя."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

        # POST — проверка
        if str(request.user.pk) == str(author_id):
            raise ValidationError({'detail': 'Нельзя подписаться на самого себя.'})

        # Создание подписки
        _, created = Subscription.objects.get_or_create(
            user=request.user,
            author_id=author_id
        )
        if not created:
            author = get_object_or_404(User, pk=author_id)
            raise ValidationError({
                'detail': f'Подписка на автора "{author.username}" уже существует.'
            })

        author = get_object_or_404(User, pk=author_id)
        return Response(
            UserWithRecipesSerializer(author, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )


# ---------------------------------------------------------
#   PERMISSIONS
# ---------------------------------------------------------

class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            request.method in permissions.SAFE_METHODS
            or obj.author_id == request.user.id
        )


# ---------------------------------------------------------
#   TAGS
# ---------------------------------------------------------

class TagViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None


# ---------------------------------------------------------
#   INGREDIENTS
# ---------------------------------------------------------

class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (AllowAny,)
    pagination_class = None

    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter


# ---------------------------------------------------------
#   RECIPES
# ---------------------------------------------------------

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

    # DRF-фильтры вместо get_queryset
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    # ---------------------------------------------------------
    #   Общий алгоритм избранного и корзины
    # ---------------------------------------------------------

    def _process_relation(self, request, model, pk):
        # сообщения для разных моделей — с подстановкой имени рецепта
        already_messages = {
            Favorite: 'Рецепт "{name}" уже в избранном.',
            ShoppingCart: 'Рецепт "{name}" уже в списке покупок.',
        }

        # СНАЧАЛА проверяем, что рецепт существует (или 404)
        recipe = get_object_or_404(Recipe, pk=pk)

        # ---- DELETE — ранний возврат ----
        if request.method == "DELETE":
            try:
                get_object_or_404(model, user=request.user, recipe=recipe).delete()
            except Http404:
                return Response(
                    {"detail": "Рецепта нет в этом списке."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)
        # ---- POST ----
        _, created = model.objects.get_or_create(
            user=request.user,
            recipe=recipe,           # вместо recipe_id=pk
        )

        if not created:
            template = already_messages.get(
                model,
                'Рецепт "{name}" уже добавлен.',
            )
            return Response(
                {"detail": template.format(name=recipe.name)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            RecipeMinifiedSerializer(
                recipe,
                context={"request": request},
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post", "delete"],
        url_path="favorite",
        permission_classes=[permissions.IsAuthenticated],
    )
    def favorite(self, request, pk=None):
        return self._process_relation(request, Favorite, pk)

    @action(
        detail=True,
        methods=["post", "delete"],
        url_path="shopping_cart",
        permission_classes=[permissions.IsAuthenticated],
    )
    def shopping_cart(self, request, pk=None):
        return self._process_relation(request, ShoppingCart, pk)

    # ---------------------------------------------------------
    #   Список покупок (скачать)
    # ---------------------------------------------------------

    @action(
        detail=False,
        methods=["get"],
        url_path="download_shopping_cart",
        permission_classes=[permissions.IsAuthenticated],
    )
    def download_shopping_cart(self, request):

        # Продукты
        products = (
            IngredientInRecipe.objects.filter(
                recipe__shopping_cart__user=request.user
            )
            .values(
                name=F("ingredient__name"),
                unit=F("ingredient__measurement_unit")
            )
            .annotate(total=Sum("amount"))
            .order_by("name")
        )

        # Рецепты
        recipes = (
            Recipe.objects.filter(shopping_cart__user=request.user)
            .select_related("author")
            .order_by("name")
        )

        text = render_shopping_list(products, recipes)
        buffer = BytesIO(text.encode("utf-8"))
        return FileResponse(
            # text,
            buffer,
            as_attachment=True,
            filename="shopping_list.txt"
        )

    # ---------------------------------------------------------
    #   Короткая ссылка
    # ---------------------------------------------------------

    @action(
        detail=True,
        methods=["get"],
        url_path="get-link",
        permission_classes=[AllowAny],
    )
    def get_link(self, request, pk=None):
        # код, однозначно восстанавливаемый обратно в id
        code = encode_id(int(pk))

        short_url = request.build_absolute_uri(
            reverse("short-link", kwargs={"code": code})
        )

        return Response({"short-link": short_url})


# ---------------------------------------------------------
#   Контроллер короткой ссылки
# ---------------------------------------------------------

class ShortLinkRedirectView(APIView):
    def get(self, request, code):
        try:
            recipe_id = decode_code(code)
        except ValueError:
            return Response({"detail": "Ссылка не найдена."}, status=404)

        recipe = get_object_or_404(Recipe, pk=recipe_id)
        url = reverse("recipe-detail", args=[recipe.id])
        return redirect(url)
