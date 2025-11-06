from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Кастомная модель пользователя с уникальным email и опциональным аватаром.
    Поля в API: id, email, username, first_name, last_name, is_subscribed, avatar
    """
    first_name = models.CharField(
        _("Имя"),
        max_length=150,
        blank=False,
        help_text=_("Имя пользователя."),
    )
    last_name = models.CharField(
        _("Фамилия"),
        max_length=150,
        blank=False,
        help_text=_("Фамилия пользователя."),
    )
    email = models.EmailField(
        _("Email"),
        unique=True,
        help_text=_("Адрес электронной почты (используется для входа)."),
    )
    avatar = models.ImageField(
        _("Аватар"),
        upload_to="avatars/",
        null=True,
        blank=True,
        help_text=_("Изображение профиля."),
    )

    username = models.CharField(
        _("Никнейм"),
        max_length=150,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[\w.@+-]+$",
                message=_(
                    "Введите корректный никнейм: допустимы только буквы, "
                    "цифры и символы @/./+/-/_."
                ),
            )
        ],
        help_text=_("Уникальное имя пользователя (никнейм)."),
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    class Meta:
        verbose_name = _("Пользователь")
        verbose_name_plural = _("Пользователи")
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
        verbose_name=_("Подписчик"),
        related_name="follows",
        on_delete=models.CASCADE,
        help_text=_("Кто подписывается."),
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Автор"),
        related_name="authors",
        on_delete=models.CASCADE,
        help_text=_("На кого подписываются."),
    )

    class Meta:
        verbose_name = _("Подписка")
        verbose_name_plural = _("Подписки")
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
