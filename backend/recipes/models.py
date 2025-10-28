from django.conf import settings
from django.db import models

class Tag(models.Model):
    name = models.CharField(max_length=32, unique=True)
    slug = models.SlugField(max_length=32, unique=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(max_length=128)
    measurement_unit = models.CharField(max_length=64)

    class Meta:
        ordering = ("name",)
        unique_together = ("name", "measurement_unit")

    def __str__(self):
        return f"{self.name} ({self.measurement_unit})"


class Recipe(models.Model):
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recipes"
    )
    name = models.CharField(max_length=200)
    text = models.TextField()
    image = models.ImageField(upload_to="recipes/")
    cooking_time = models.PositiveIntegerField()
    tags = models.ManyToManyField(Tag, related_name="recipes")

    class Meta:
        ordering = ("-id",)
        constraints = [
            models.CheckConstraint(check=models.Q(cooking_time__gt=0), name="recipe_cooking_time_gt_0"),
        ]

    def __str__(self):
        return self.name


class IngredientInRecipe(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="recipe_ingredients")
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name="ingredient_recipes")
    amount = models.PositiveIntegerField()

    class Meta:
        unique_together = ("recipe", "ingredient")
        constraints = [
            models.CheckConstraint(check=models.Q(amount__gt=0), name="ingredient_in_recipe_amount_gt_0"),
        ]

class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="favorited_by")

    class Meta:
        unique_together = ("user", "recipe")


class ShoppingCart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart_items")
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="in_carts")

    class Meta:
        unique_together = ("user", "recipe")
