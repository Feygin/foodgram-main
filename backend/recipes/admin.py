from django.contrib import admin
from django.db.models import Count

from .models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                     ShoppingCart, Tag)


class IngredientInRecipeInline(admin.TabularInline):
    model = IngredientInRecipe
    extra = 0
    autocomplete_fields = ("ingredient",)
    min_num = 1


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "measurement_unit")
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """
    - в списке: название и автор
    - поиск: по автору и названию
    - фильтрация: по тегам
    - на странице рецепта: вывести общее число добавлений в избранное
    """

    list_display = ("id", "name", "author", "favorites_count")
    list_select_related = ("author",)
    search_fields = (
        "name",
        "author__username",
        "author__email",
        "author__first_name",
        "author__last_name",
    )
    list_filter = ("tags",)
    inlines = (IngredientInRecipeInline,)
    readonly_fields = ("favorites_total",)
    fields = (
        ("name", "author"),
        "image",
        "text",
        "cooking_time",
        "tags",
        "favorites_total",
    )
    autocomplete_fields = ("tags",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_fav_count=Count("favorited_by"))

    @admin.display(description="В избранном", ordering="_fav_count")
    def favorites_count(self, obj):
        return getattr(obj, "_fav_count", obj.favorited_by.count())

    @admin.display(description="Количество добавлений в избранное")
    def favorites_total(self, obj):
        return obj.favorited_by.count()


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "recipe")
    list_select_related = ("user", "recipe")
    search_fields = (
        "user__email",
        "user__username",
        "recipe__name",
        "recipe__author__email",
        "recipe__author__username",
    )
    autocomplete_fields = ("user", "recipe")


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "recipe")
    list_select_related = ("user", "recipe")
    search_fields = (
        "user__email",
        "user__username",
        "recipe__name",
        "recipe__author__email",
        "recipe__author__username",
    )
    autocomplete_fields = ("user", "recipe")


@admin.register(IngredientInRecipe)
class IngredientInRecipeAdmin(admin.ModelAdmin):
    list_display = ("id", "recipe", "ingredient", "amount")
    list_select_related = ("recipe", "ingredient")
    search_fields = ("recipe__name", "ingredient__name")
    autocomplete_fields = ("recipe", "ingredient")
