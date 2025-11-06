from api.pagination import LimitPageNumberPagination
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from djoser.views import UserViewSet as DjoserUserViewSet
from djoser.serializers import UserCreateSerializer, PasswordSerializer
from rest_framework import permissions, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

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
    permission_classes = (permissions.AllowAny,)
    pagination_class = LimitPageNumberPagination
    serializer_class = UserSerializer  # базовый сериализатор для list/retrieve

    # По требованию ревьюера: perform-версия create
    def perform_create(self, serializer: UserCreateSerializer):
        serializer.save()

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
        # Используем related_name: у автора related_name='subscriptions', поэтому:
        # все авторы, на которых подписан текущий пользователь
        authors_qs = User.objects.filter(subscriptions__user=request.user)
        page = self.paginate_queryset(authors_qs)
        serializer = UserWithRecipesSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post', 'delete'], url_path='subscribe', permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, pk=None):
        # Ранний возврат для DELETE
        if request.method.lower() == 'delete':
            # Никаких лишних запросов к автору: удаляем по ключам
            get_object_or_404(Subscription, user=request.user, author_id=pk).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        # POST — проверки и создание
        if str(request.user.pk) == str(pk):
            # перевод + валидационное исключение вместо 400 вручную
            raise ValidationError({'detail': _('Нельзя подписаться на самого себя.')})

        # попробуем создать подписку; если уже есть — сообщаем валидатором
        _, created = Subscription.objects.get_or_create(user=request.user, author_id=pk)
        if not created:
            # Уточняем «на кого» уже подписка
            author = get_object_or_404(User, pk=pk)
            raise ValidationError({'detail': _('Подписка на автора "%(name)s" уже существует.') % {'name': author.username}})

        # Возвращаем публичные данные автора (+рецепты/счётчик)
        author = get_object_or_404(User, pk=pk)
        return Response(UserWithRecipesSerializer(author, context={'request': request}).data, status=status.HTTP_201_CREATED)
