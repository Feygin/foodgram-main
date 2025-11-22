from djoser.serializers import (
    UserCreateSerializer as DjoserUserCreateSerializer,
    UserSerializer as DjoserUserSerializer,
)
from recipes.models import Subscription, User
from rest_framework import serializers

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
                user=request.user, author=user
            ).exists()
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
        fields = (*UserSerializer.Meta.fields,
            "recipes", "recipes_count")
        read_only_fields = fields

    def get_recipes(self, user):
        from .recipes import RecipeMinifiedSerializer
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
