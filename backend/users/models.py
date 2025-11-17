from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


class User(AbstractUser):
    """
    Кастомная модель пользователя.
    Поля в API: id, email, username, first_name, last_name, is_subscribed, avatar
    """

    first_name = models.CharField(
        "Имя",
        max_length=150,
        help_text="Имя пользователя.",
    )
    last_name = models.CharField(
        "Фамилия",
        max_length=150,
        help_text="Фамилия пользователя.",
    )
    email = models.EmailField(
        "Email",
        max_length=254,
        unique=True,
        help_text="Адрес электронной почты (используется для входа).",
    )
    avatar = models.ImageField(
        "Аватар",
        upload_to="avatars/",
        null=True,
        blank=True,
        help_text="Изображение профиля.",
    )

    username = models.CharField(
        "Никнейм",
        max_length=150,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[\w.@+-]+$",
                message=(
                    "Введите корректный никнейм: допустимы только буквы, "
                    "цифры и символы @/./+/-/_"
                ),
            )
        ],
        help_text="Уникальное имя пользователя (никнейм).",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ("last_name", "first_name", "id")

    def __str__(self):
        return self.email or self.username


class Subscription(models.Model):
    """
    Подписка: подписчик (user) подписывается на автора (author).
    Пары (user, author) уникальны.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Подписчик",
        related_name="follows",
        on_delete=models.CASCADE,
        help_text="Кто подписывается.",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Автор",
        related_name="authors",
        on_delete=models.CASCADE,
        help_text="На кого подписываются.",
    )

    class Meta:
        verbose_name = "Подписка"
        verbose_name_plural = "Подписки"
        ordering = ("author", "user")
        constraints = [
            models.UniqueConstraint(
                fields=["user", "author"],
                name="users_subscription_unique_user_author",
            ),
            models.CheckConstraint(
                check=~models.Q(user=models.F("author")),
                name="users_subscription_no_self_follow",
            ),
        ]

    def __str__(self):
        return f"{self.user_id} → {self.author_id}"
