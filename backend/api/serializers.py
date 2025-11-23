from collections import Counter

from djoser.serializers import UserSerializer as DjoserUserSerializer
from rest_framework import serializers

from recipes.models import (
    MIN_COOKING_TIME,
    MIN_INGREDIENT_AMOUNT,
    Ingredient,
    IngredientInRecipe,
    Recipe,
    Subscription,
    Tag,
    User,
)

from .fields import Base64ImageField


class UserSerializer(DjoserUserSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta(DjoserUserSerializer.Meta):
        model = User
        fields = (*DjoserUserSerializer.Meta.fields, "is_subscribed", "avatar")
        read_only_fields = fields

    def get_is_subscribed(self, user):
        request = self.context.get("request")
        return (
            request
            and request.user.is_authenticated
            and Subscription.objects.filter(
                user=request.user, author=user).exists()
        )


class AvatarSerializer(serializers.Serializer):
    avatar = Base64ImageField(required=True)

    def update(self, instance, validated_data):
        instance.avatar = validated_data["avatar"]
        instance.save(update_fields=["avatar"])
        return instance

    def create(self, validated_data):
        raise NotImplementedError


class UserWithRecipesSerializer(UserSerializer):
    recipes_count = serializers.IntegerField(
        read_only=True, source="recipes.count")
    recipes = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = (*UserSerializer.Meta.fields, "recipes", "recipes_count")
        read_only_fields = fields

    def get_recipes(self, user):

        request = self.context.get("request")
        try:
            limit = int(request.query_params.get("recipes_limit", 0))
        except Exception:
            limit = 10**10

        qs = user.recipes.all()
        qs = qs[:limit]

        return RecipeMinifiedSerializer(
            qs, many=True, context={"request": request}
        ).data


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
        extra_kwargs = {
            "ingredients": {"required": True},
            "tags": {"required": True},
        }

    def validate(self, attrs):
        if self.instance:
            if "ingredients" not in attrs:
                raise serializers.ValidationError(
                    {"ingredients": "Это поле обязательное."}
                )
            if "tags" not in attrs:
                raise serializers.ValidationError(
                    {"tags": "Это поле обязательное."})
        return super().validate(attrs)

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError("Нужен хотя бы один тег.")

        ids = [tag.id for tag in value]
        duplicates = _get_duplicates(ids)

        if duplicates:
            raise serializers.ValidationError(
                "Теги должны быть уникальными. Повторяются: "
                + ", ".join(str(x) for x in duplicates)
            )
        return value

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError("Нужен хотя бы один ингредиент.")

        ids = [getattr(item["id"], "id", item["id"]) for item in value]
        duplicates = _get_duplicates(ids)
        if duplicates:
            raise serializers.ValidationError(
                "Ингредиенты должны быть уникальными. Повторяются: "
                + ", ".join(str(x) for x in duplicates)
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
        items = validated_data.pop("ingredients")
        tags = validated_data.pop("tags")

        instance.tags.set(tags)

        IngredientInRecipe.objects.filter(recipe=instance).delete()
        self._set_ingredients(instance, items)

        return super().update(instance, validated_data)

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
        return (user.is_authenticated
                and recipe.favorites.filter(user=user).exists())

    def get_is_in_shopping_cart(self, recipe):
        user = self.context["request"].user
        return (user.is_authenticated
                and recipe.shopping_cart.filter(user=user).exists())


def _get_duplicates(values):
    return {item for item, count in Counter(values).items() if count > 1}
