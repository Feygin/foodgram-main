from api.pagination import LimitPageNumberPagination
from django.contrib.auth import get_user_model
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Subscription
from .serializers import (AvatarSerializer, PasswordChangeSerializer,
                          SubscriptionSerializer, UserCreateSerializer,
                          UserListSerializer, UserPublicSerializer,
                          UserSerializer)

User = get_user_model()


class UsersViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('id')
    permission_classes = (permissions.AllowAny,)
    pagination_class = LimitPageNumberPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return UserListSerializer
        if self.action == 'retrieve':
            return UserSerializer
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ('subscriptions', 'subscribe'):
            return SubscriptionSerializer
        # Fallback (used by /users/me/, set_password, avatar)
        return UserSerializer

    def get_permissions(self):
        # Auth-only for protected actions
        if self.action in ('me', 'set_password',
                           'avatar', 'subscriptions', 'subscribe'):
            return (permissions.IsAuthenticated(),)
        return super().get_permissions()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        serializer = self.get_serializer(
            page if page is not None else queryset,
            many=True, context={'request': request})
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        create_serializer = UserCreateSerializer(
            data=request.data, context={'request': request})
        create_serializer.is_valid(raise_exception=True)
        user = create_serializer.save()
        response_serializer = UserPublicSerializer(
            user, context={'request': request})
        headers = self.get_success_headers(response_serializer.data)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='set_password')
    def set_password(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['put', 'delete'], url_path='me/avatar')
    def avatar(self, request):
        user = request.user
        if request.method.lower() == 'delete':
            if user.avatar:
                user.avatar.delete(save=False)
            user.avatar = None
            user.save(update_fields=['avatar'])
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = AvatarSerializer(
            instance=user, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {'avatar': request.build_absolute_uri(user.avatar.url)})

    @action(detail=False, methods=['get'], url_path='subscriptions')
    def subscriptions(self, request):
        subs = Subscription.objects.filter(
            user=request.user).values_list('author_id', flat=True)
        authors = User.objects.filter(id__in=subs).order_by('id')
        page = self.paginate_queryset(authors)
        serializer = SubscriptionSerializer(
            page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['post', 'delete'], url_path='subscribe')
    def subscribe(self, request, pk=None):
        author = self.get_object()
        if request.method.lower() == 'post':
            if author == request.user:
                return Response(
                    {'detail': 'You cannot subscribe to yourself.'},
                    status=status.HTTP_400_BAD_REQUEST)
            obj, created = Subscription.objects.get_or_create(
                user=request.user, author=author)
            if not created:
                return Response(
                    {'detail': 'Already subscribed.'},
                    status=status.HTTP_400_BAD_REQUEST)
            data = SubscriptionSerializer(
                author, context={'request': request}).data
            return Response(data, status=status.HTTP_201_CREATED)

        deleted, _ = Subscription.objects.filter(
            user=request.user, author=author).delete()
        if not deleted:
            return Response(
                {'detail': 'Not subscribed.'},
                status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_204_NO_CONTENT)
