from api.pagination import LimitPageNumberPagination
from api.serializers import (
    AvatarSerializer,
    UserSerializer,
    UserWithRecipesSerializer,
)
from django.contrib.auth import get_user_model
from django.http import Http404
from django.shortcuts import get_object_or_404
from djoser.serializers import UserCreateSerializer
from djoser.views import UserViewSet as DjoserUserViewSet
from recipes.models import Subscription
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

User = get_user_model()


class UsersViewSet(DjoserUserViewSet):
    queryset = User.objects.all()
    pagination_class = LimitPageNumberPagination
    serializer_class = UserSerializer

    def perform_create(self, serializer: UserCreateSerializer):
        serializer.save()

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthenticated])
    def me(self, request, *args, **kwargs):
        return super().me(request, *args, **kwargs)

    @action(
        detail=False,
        methods=['put', 'delete'],
        url_path='me/avatar',
        permission_classes=[permissions.IsAuthenticated]
    )
    def avatar(self, request):

        if request.method.lower() == 'delete':
            if request.user.avatar:
                request.user.avatar.delete(save=False)
            request.user.avatar = None
            request.user.save(update_fields=['avatar'])
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = AvatarSerializer(
            instance=request.user,
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({
            'avatar': request.build_absolute_uri(request.user.avatar.url)
        })

    @action(
        detail=False,
        methods=['get'],
        url_path='subscriptions',
        permission_classes=[permissions.IsAuthenticated]
    )
    def subscriptions(self, request):
        authors_qs = User.objects.filter(authors__user=request.user)
        page = self.paginate_queryset(authors_qs)
        serializer = UserWithRecipesSerializer(
            page, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='subscribe',
        permission_classes=[permissions.IsAuthenticated]
    )
    def subscribe(self, request, *args, **kwargs):
        author_id = kwargs.get(self.lookup_field)

        author = get_object_or_404(User, pk=author_id)

        if request.method.lower() == 'delete':
            try:
                get_object_or_404(
                    Subscription,
                    user=request.user,
                    author_id=author_id
                ).delete()
            except Http404:
                return Response(
                    {"detail": "Вы не подписаны на этого пользователя."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

        if str(request.user.pk) == str(author_id):
            raise ValidationError({"detail": "Нельзя подписаться на себя."})

        _, created = Subscription.objects.get_or_create(
            user=request.user,
            author_id=author_id
        )

        if not created:
            raise ValidationError({
                "detail": f'Подписка на "{author.username}" уже существует.'
            })

        return Response(
            UserWithRecipesSerializer(
                author, context={'request': request}
            ).data,
            status=status.HTTP_201_CREATED
        )
