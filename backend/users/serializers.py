from django.contrib.auth.password_validation import validate_password
from django.core.validators import validate_email
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from .models import User, Subscription
from api.fields import Base64ImageField  # your local field (no extra deps)

# If you need the minified recipe in subscriptions
from recipes.serializers import RecipeMinifiedSerializer
from recipes.models import Recipe


class UserListSerializer(serializers.ModelSerializer):
    """Used for GET /api/users/ (list). Includes avatar, excludes is_subscribed."""
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name', 'avatar')


class UserPublicSerializer(serializers.ModelSerializer):
    """Minimal shape for list/retrieve: id, email, username, first_name, last_name."""
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'first_name', 'last_name')

class UserSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar',
        )
        read_only_fields = ('id', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return Subscription.objects.filter(user=request.user, author=obj).exists()


class UserCreateSerializer(serializers.ModelSerializer):
    """
    For registration (POST /users/). If you rely entirely on Djoser, you can
    point DJOSER['SERIALIZERS']['user_create'] to this class.
    """
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name', 'last_name', 'password')

    def validate_email(self, value):
        validate_email(value)
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs.get('current_password')):
            raise serializers.ValidationError({'current_password': _('Incorrect password.')})
        validate_password(attrs.get('new_password'), user)
        return attrs


class AvatarSerializer(serializers.Serializer):
    """
    Accepts either multipart file (ImageField) or base64 via our Base64ImageField.
    Returns {"avatar": "<absolute_url>"}.
    """
    avatar = Base64ImageField(required=True)

    def update(self, instance, validated_data):
        instance.avatar = validated_data['avatar']
        instance.save(update_fields=['avatar'])
        return instance

    def create(self, validated_data):
        # Not used; we update request.user
        raise NotImplementedError


class SubscriptionSerializer(serializers.ModelSerializer):
    """
    For /users/subscriptions/ and POST /users/{id}/subscribe/ responses.
    Includes embedded recipes with ?recipes_limit and recipes_count.
    """
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    avatar = serializers.ImageField(read_only=True)

    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_subscribed', 'avatar', 'recipes', 'recipes_count',
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return Subscription.objects.filter(user=request.user, author=obj).exists()

    def get_recipes(self, obj):
        request = self.context.get('request')
        try:
            limit = int(request.query_params.get('recipes_limit', 0))
        except Exception:
            limit = 0

        qs = Recipe.objects.filter(author=obj).order_by('-id')
        if limit and limit > 0:
            qs = qs[:limit]
        return RecipeMinifiedSerializer(qs, many=True, context={'request': request}).data

    def get_recipes_count(self, obj):
        return Recipe.objects.filter(author=obj).count()
