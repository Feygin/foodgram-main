from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator, MinValueValidator

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


class Tag(models.Model):
    name = models.CharField(
        "Название",
        max_length=32,
        unique=True,
    )
    slug = models.SlugField(
        "Слаг",
        max_length=32,
        unique=True,
    )

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"
        ordering = ("name",)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField("Название", max_length=128)
    measurement_unit = models.CharField("Единица измерения", max_length=64)

    class Meta:
        verbose_name = "Ингредиент"
        verbose_name_plural = "Ингредиенты"
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("name", "measurement_unit"),
                name="uniq_ingredient_name_unit",
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.measurement_unit})"


class Recipe(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="recipes",
        verbose_name="Автор",
    )
    name = models.CharField("Название", max_length=200)
    text = models.TextField("Описание")
    image = models.ImageField("Изображение", upload_to="recipes/")
    cooking_time = models.PositiveIntegerField(
        "Время приготовления, мин",
        validators=[MinValueValidator(1)],
    )
    tags = models.ManyToManyField(
        Tag,
        related_name="recipes",
        verbose_name="Теги",
    )
    created = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        verbose_name = "Рецепт"
        verbose_name_plural = "Рецепты"
        # Предметная сортировка: сначала новые рецепты, затем по названию.
        ordering = ("-created", "name")

    def __str__(self):
        return self.name


class IngredientInRecipe(models.Model):
    """
    Связующая модель для рецепта и ингредиента с количеством.
    related_name у обеих сторон повторяет одно значение по требованию ревьюера.
    """
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",
        verbose_name="Рецепт",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="recipe_ingredients",  # повторяем значение со строки выше
        verbose_name="Ингредиент",
    )
    amount = models.PositiveIntegerField(
        "Количество",
        validators=[MinValueValidator(1)],
    )

    class Meta:
        verbose_name = "Ингредиент в рецепте"
        verbose_name_plural = "Ингредиенты в рецептах"
        constraints = [
            models.UniqueConstraint(
                fields=("recipe", "ingredient"),
                name="uniq_recipe_ingredient_pair",
            ),
        ]

    def __str__(self):
        return f"{self.ingredient} — {self.amount}"


class UserRecipeRelation(models.Model):
    """
    Базовый класс для моделей «Избранное» и «Корзина».
    Содержит:
    - два поля (user, recipe),
    - валидацию уникальности пары полей,
    - человекочитаемый __str__.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="Пользователь",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name="Рецепт",
    )

    class Meta:
        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=("user", "recipe"),
                name="uniq_%(app_label)s_%(class)s_user_recipe",
            ),
        ]

    def __str__(self):
        return f"{self.user} — {self.recipe}"


class Favorite(UserRecipeRelation):
    """
    Модель избранных рецептов.
    Наследует поля user и recipe из UserRecipeRelation.
    Здесь оставляем только локализацию.
    """

    class Meta(UserRecipeRelation.Meta):
        default_related_name = 'favorites'
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"


class ShoppingCart(UserRecipeRelation):
    """
    Модель корзины покупок.
    Наследует поля user и recipe из UserRecipeRelation.
    Здесь оставляем только локализацию.
    """

    class Meta(UserRecipeRelation.Meta):
        default_related_name = 'shopping_cart'
        verbose_name = "Корзина"
        verbose_name_plural = "Корзина"