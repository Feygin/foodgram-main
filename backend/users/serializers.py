from api.fields import Base64ImageField
from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from django.utils.translation import gettext_lazy as _
from recipes.models import Recipe
from recipes.serializers import RecipeMinifiedSerializer
from rest_framework import serializers

from .models import Subscription, User


class UserListSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ("id", "email", "username",
                  "first_name", "last_name", "avatar")


class UserPublicSerializer(serializers.ModelSerializer):

    class Meta:
        model = User
        fields = ("id", "email", "username", "first_name", "last_name")


class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "avatar",
        )
        read_only_fields = ("id", "is_subscribed", "avatar")

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return Subscription.objects.filter(
            user=request.user, author=obj).exists()


class UserCreateSerializer(serializers.ModelSerializer):

    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("email", "username", "first_name", "last_name", "password")

    def validate_email(self, value):
        validate_email(value)
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs.get("current_password")):
            raise serializers.ValidationError(
                {"current_password": _("Incorrect password.")}
            )
        validate_password(attrs.get("new_password"), user)
        return attrs


class AvatarSerializer(serializers.Serializer):

    avatar = Base64ImageField(required=True)

    def update(self, instance, validated_data):
        instance.avatar = validated_data["avatar"]
        instance.save(update_fields=["avatar"])
        return instance

    def create(self, validated_data):
        raise NotImplementedError


class SubscriptionSerializer(serializers.ModelSerializer):

    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    avatar = serializers.ImageField(read_only=True)

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "is_subscribed",
            "avatar",
            "recipes",
            "recipes_count",
        )

    def get_is_subscribed(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return Subscription.objects.filter(
            user=request.user, author=obj).exists()

    def get_recipes(self, obj):
        request = self.context.get("request")
        try:
            limit = int(request.query_params.get("recipes_limit", 0))
        except Exception:
            limit = 0

        qs = Recipe.objects.filter(author=obj).order_by("-id")
        if limit and limit > 0:
            qs = qs[:limit]
        return RecipeMinifiedSerializer(
            qs, many=True, context={"request": request}
        ).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()
