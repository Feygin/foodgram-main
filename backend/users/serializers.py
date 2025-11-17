from api.fields import Base64ImageField
from djoser.serializers import UserSerializer as DjoserUserSerializer
from djoser.serializers import PasswordSerializer
from djoser.serializers import UserCreateSerializer as DjoserUserCreateSerializer

from recipes.models import Recipe
from rest_framework import serializers

from .models import Subscription, User


class UserSerializer(DjoserUserSerializer):
    """
    Публичный сериализатор пользователя на базе Djoser.
    Расширяем базовые поля на is_subscribed и avatar.
    Все поля делаем только для чтения (безопасно для любых обработчиков).
    """
    is_subscribed = serializers.SerializerMethodField()

    class Meta(DjoserUserSerializer.Meta):
        model = User
        # расширяем поля базового класса
        fields = DjoserUserSerializer.Meta.fields + ("is_subscribed", "avatar")
        # защита от случайных изменений
        read_only_fields = DjoserUserSerializer.Meta.fields + ("is_subscribed", "avatar")

    def get_is_subscribed(self, user):
        request = self.context.get("request")
        return (
            request
            and request.user.is_authenticated
            and Subscription.objects.filter(user=request.user, author=user).exists()
        )

class UserCreateSerializer(DjoserUserCreateSerializer):
    """
    Используем базовый сериализатор Djoser для создания пользователя.
    Добавлять ничего не нужно — Djoser уже реализует хеширование пароля,
    валидацию и создание пользователя.
    """
    class Meta(DjoserUserCreateSerializer.Meta):
        model = User
        fields = ("email", "id", "username", "first_name", "last_name", "password")

class AvatarSerializer(serializers.Serializer):
    """
    Сериализатор обновления аватара. Djoser покрывает пользователи/пароли,
    а аватар — отдельный эндпоинт с Base64ImageField.
    """
    avatar = Base64ImageField(required=True)

    def update(self, instance, validated_data):
        instance.avatar = validated_data["avatar"]
        instance.save(update_fields=["avatar"])
        return instance

    def create(self, validated_data):
        raise NotImplementedError


class UserWithRecipesSerializer(UserSerializer):
    """
    Расширенный публичный пользователь с кратким списком рецептов и их количеством.
    Ранее назывался SubscriptionSerializer — имя сбивало с толку.
    """
    # количество рецептов получаем через related_name без метода
    # DRF вызовет .count() у related manager
    recipes_count = serializers.IntegerField(read_only=True, source="recipes.count")
    # список рецептов оставим метод-поле (нам нужен параметр recipes_limit)
    recipes = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        # добавляем два поля к базовому набору из UserSerializer
        fields = tuple(UserSerializer.Meta.fields) + ("recipes", "recipes_count")
        read_only_fields = fields  # полностью только для чтения

    def get_recipes(self, user):
        from recipes.serializers import RecipeMinifiedSerializer
        request = self.context.get("request")
        try:
            limit = int(request.query_params.get("recipes_limit", 0)) if request else 0
        except Exception:
            limit = 0

        # используем связь по related_name вместо фильтра по модели
        qs = getattr(user, "recipes").all()
        if limit and limit > 0:
            qs = qs[:limit]
        return RecipeMinifiedSerializer(qs, many=True, context={"request": request}).data
