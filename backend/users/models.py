from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


class User(AbstractUser):
    """
    Custom user with unique email and optional avatar.
    Fields returned by API: id, email, username,
    first_name, last_name, is_subscribed, avatar
    """
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)
    email = models.EmailField('email address', unique=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[\w.@+-]+$',
                message=(
                    'Enter a valid username. '
                    'This value may contain only letters, '
                    'numbers, and @/./+/-/_ characters.',
                )
            )
        ],
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        ordering = ('id',)

    def __str__(self):
        return self.email or self.username


class Subscription(models.Model):
    """
    Follower (user) subscribes to author (user). Unique pairs only.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='follows', on_delete=models.CASCADE
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='followers', on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ('user', 'author')
        constraints = [
            models.CheckConstraint(
                check=~models.Q(user=models.F('author')),
                name='users_subscription_no_self_follow',
            )
        ]

    def __str__(self):
        return f'{self.user_id} → {self.author_id}'
