from api.fields import Base64ImageField
from rest_framework import serializers
from users.serializers import UserSerializer

from .models import Ingredient, IngredientInRecipe, Recipe, Tag


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


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recipe
        fields = ("id", "name", "image", "cooking_time")


class RecipeIngredientWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    amount = serializers.IntegerField(min_value=1)


class RecipeWriteSerializer(serializers.ModelSerializer):
    image = Base64ImageField()
    ingredients = RecipeIngredientWriteSerializer(many=True, write_only=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(), many=True, write_only=True
    )

    class Meta:
        model = Recipe
        fields = ("ingredients", "tags", "image",
                  "name", "text", "cooking_time")

    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "cooking_time must be at least 1.")
        return value

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError("At least one tag is required.")
        ids = [t.id for t in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Tags must be unique.")
        return value

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one ingredient is required.")

        ids = [item["id"] for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Ingredients must be unique.")

        existing = set(
            Ingredient.objects.filter(id__in=ids).values_list("id", flat=True)
        )
        missing = sorted(set(ids) - existing)
        if missing:
            raise serializers.ValidationError(
                f"Unknown ingredient ids: {', '.join(map(str, missing))}"
            )

        return value

    def create(self, validated_data):
        items = validated_data.pop("ingredients")
        tags = validated_data.pop("tags")
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self._set_ingredients(recipe, items)
        return recipe

    def update(self, instance, validated_data):
        items = validated_data.pop("ingredients", None)
        tags = validated_data.pop("tags", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if tags is not None:
            instance.tags.set(tags)
        if items is not None:
            IngredientInRecipe.objects.filter(recipe=instance).delete()
            self._set_ingredients(instance, items)
        return instance

    def _set_ingredients(self, recipe, items):
        # single DB hit for all ingredients
        by_id = Ingredient.objects.in_bulk([i["id"] for i in items])
        bulk = [
            IngredientInRecipe(
                recipe=recipe,
                ingredient=by_id[item["id"]],
                amount=item["amount"],
            )
            for item in items
        ]
        IngredientInRecipe.objects.bulk_create(bulk)

    def to_representation(self, instance):
        return RecipeReadSerializer(instance, context=self.context).data


class RecipeReadSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientInRecipeReadSerializer(
        source="recipe_ingredients", many=True, read_only=True
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

    def get_author(self, obj):
        return UserSerializer(obj.author, context=self.context).data

    def get_is_favorited(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        return obj.favorited_by.filter(user=user).exists()

    def get_is_in_shopping_cart(self, obj):
        user = self.context["request"].user
        if not user.is_authenticated:
            return False
        return obj.in_carts.filter(user=user).exists()
