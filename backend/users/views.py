from api.pagination import LimitPageNumberPagination
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet as DjoserUserViewSet
from djoser.serializers import UserCreateSerializer
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Subscription
from .serializers import AvatarSerializer, UserSerializer, UserWithRecipesSerializer

User = get_user_model()


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
        authors_qs = User.objects.filter(subscriptions__user=request.user)
        page = self.paginate_queryset(authors_qs)
        serializer = UserWithRecipesSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post', 'delete'], url_path='subscribe', permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, pk=None):
        # DELETE — отписка
        if request.method.lower() == 'delete':
            get_object_or_404(Subscription, user=request.user, author_id=pk).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # POST — проверки
        if str(request.user.pk) == str(pk):
            raise ValidationError({'detail': 'Нельзя подписаться на самого себя.'})

        # Попытка создать подписку
        _, created = Subscription.objects.get_or_create(user=request.user, author_id=pk)
        if not created:
            author = get_object_or_404(User, pk=pk)
            raise ValidationError({
                'detail': f'Подписка на автора "{author.username}" уже существует.'
            })

        # Возвращаем данные автора
        author = get_object_or_404(User, pk=pk)
        return Response(
            UserWithRecipesSerializer(author, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
