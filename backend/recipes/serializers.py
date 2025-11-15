from api.fields import Base64ImageField
from rest_framework import serializers

from .models import Ingredient, IngredientInRecipe, Recipe, Tag
from users.serializers import UserSerializer


MIN_INGREDIENT_AMOUNT = 1
MIN_COOKING_TIME = 1


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
            and recipe.favorited_by.filter(user=user).exists()
        )

    def get_is_in_shopping_cart(self, recipe):
        user = self.context["request"].user
        return (
            user.is_authenticated
            and recipe.in_carts.filter(user=user).exists()
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
