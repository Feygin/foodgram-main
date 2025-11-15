# recipes/models.py
from django.conf import settings
from django.db import models


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
    cooking_time = models.PositiveIntegerField("Время приготовления, мин")
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
    amount = models.PositiveIntegerField("Количество")

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
        related_name="%(class)s",  # user.favorite / user.shoppingcart
        verbose_name="Пользователь",
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name="%(class)s",  # recipe.favorite / recipe.shoppingcart
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
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"


class ShoppingCart(UserRecipeRelation):
    """
    Модель корзины покупок.
    Наследует поля user и recipe из UserRecipeRelation.
    Здесь оставляем только локализацию.
    """

    class Meta(UserRecipeRelation.Meta):
        verbose_name = "Корзина"
        verbose_name_plural = "Корзина"