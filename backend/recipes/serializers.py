from api.fields import Base64ImageField
from djoser.serializers import UserSerializer as DjoserUserSerializer
from djoser.serializers import PasswordSerializer
from djoser.serializers import UserCreateSerializer as DjoserUserCreateSerializer
from rest_framework import serializers

from .models import Ingredient, IngredientInRecipe, Recipe, Tag, Subscription, User


MIN_INGREDIENT_AMOUNT = 1
MIN_COOKING_TIME = 1

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

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ("id", "name", "slug")
        read_only_fields = fields


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ("id", "name", "measurement_unit")
        read_only_fields = fields


class IngredientInRecipeReadSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="ingredient.id", read_only=True)
    name = serializers.CharField(source="ingredient.name", read_only=True)
    measurement_unit = serializers.CharField(
        source="ingredient.measurement_unit", read_only=True
    )

    class Meta:
        model = IngredientInRecipe
        fields = ("id", "name", "measurement_unit", "amount")
        read_only_fields = fields


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")
        read_only_fields = fields


class RecipeIngredientWriteSerializer(serializers.Serializer):
    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(min_value=MIN_INGREDIENT_AMOUNT)


class RecipeWriteSerializer(serializers.ModelSerializer):
    image = Base64ImageField()
    ingredients = RecipeIngredientWriteSerializer(many=True, write_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        write_only=True,
    )
    cooking_time = serializers.IntegerField(min_value=MIN_COOKING_TIME)

    class Meta:
        model = Recipe
        fields = (
            "ingredients",
            "tags",
            "image",
            "name",
            "text",
            "cooking_time",
        )

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError("Нужен хотя бы один тег.")

        ids = [tag.id for tag in value]
        duplicates = _get_duplicates(ids)

        if duplicates:
            raise serializers.ValidationError(
                "Теги должны быть уникальными. Повторяются: "
                + ", ".join(map(str, sorted(duplicates)))
            )
        return value


    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError("Нужен хотя бы один ингредиент.")

        ids = [
            getattr(item["id"], "id", item["id"])
            for item in value
        ]
        duplicates = _get_duplicates(ids)

        if duplicates:
            raise serializers.ValidationError(
                "Ингредиенты должны быть уникальными. Повторяются: "
                + ", ".join(map(str, sorted(duplicates)))
            )

        return value

    def create(self, validated_data):
        items = validated_data.pop("ingredients")
        tags = validated_data.pop("tags")
        recipe = super().create(validated_data)
        recipe.tags.set(tags)
        self._set_ingredients(recipe, items)
        return recipe

    def update(self, instance, validated_data):
        if "ingredients" not in validated_data or "tags" not in validated_data:
            raise serializers.ValidationError({
                "ingredients": ["This field is required."],
                "tags": ["This field is required."]
            })
        items = validated_data.pop("ingredients")
        tags = validated_data.pop("tags")
        instance = super().update(instance, validated_data)
        instance.tags.set(tags)
        IngredientInRecipe.objects.filter(recipe=instance).delete()
        self._set_ingredients(instance, items)
        return instance

    def _set_ingredients(self, recipe, items):
        bulk = [
            IngredientInRecipe(
                recipe=recipe,
                ingredient_id=getattr(item["id"], "id", item["id"]),
                amount=item["amount"],
            )
            for item in items
        ]
        IngredientInRecipe.objects.bulk_create(bulk)

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class RecipeReadSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientInRecipeReadSerializer(
        source="recipe_ingredients",
        many=True,
        read_only=True,
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )
        read_only_fields = fields

    def get_is_favorited(self, recipe):
        user = self.context["request"].user
        return (
            user.is_authenticated
            and recipe.favorites.filter(user=user).exists()
        )

    def get_is_in_shopping_cart(self, recipe):
        user = self.context["request"].user
        return (
            user.is_authenticated
            and recipe.shopping_cart.filter(user=user).exists()
        )


def _get_duplicates(values):
    """
    Helper to return a set of duplicated values in the given iterable.
    Preserves only items that appear more than once.
    """
    seen = set()
    duplicates = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        else:
            seen.add(value)
    return duplicates
