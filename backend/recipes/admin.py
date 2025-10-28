from django.contrib import admin
from django.db.models import Count
from .models import (
    Tag, Ingredient, Recipe, IngredientInRecipe,
    Favorite, ShoppingCart
)

# --- Inlines -------------------------------------------------

class IngredientInRecipeInline(admin.TabularInline):
    model = IngredientInRecipe
    extra = 0
    autocomplete_fields = ('ingredient',)
    min_num = 1


# --- Tag -----------------------------------------------------

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)


# --- Ingredient ----------------------------------------------

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')  # ✔ название и единица измерения
    search_fields = ('name',)                           # ✔ поиск по названию
    ordering = ('name',)


# --- Recipe --------------------------------------------------

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """
    Требования:
    - в списке: название и автор ✔
    - поиск: по автору и названию ✔
    - фильтрация: по тегам ✔
    - на странице рецепта: вывести общее число добавлений в избранное ✔
    """
    list_display = ('id', 'name', 'author', 'favorites_count')   # ✔
    list_select_related = ('author',)
    search_fields = (                                             # ✔
        'name',
        'author__username', 'author__email',
        'author__first_name', 'author__last_name',
    )
    list_filter = ('tags',)                                       # ✔ фильтр по тегам
    inlines = (IngredientInRecipeInline,)
    readonly_fields = ('favorites_total',)                        # ✔ поле на карточке
    fields = (
        ('name', 'author'),
        'image',
        'text',
        'cooking_time',
        'tags',
        'favorites_total',  # read-only display on the form
    )
    autocomplete_fields = ('tags',)

    def get_queryset(self, request):
        # annotate favorites count for fast list display
        qs = super().get_queryset(request)
        return qs.annotate(_fav_count=Count('favorited_by'))

    @admin.display(description='В избранном', ordering='_fav_count')
    def favorites_count(self, obj):
        # used in list_display
        return getattr(obj, '_fav_count', obj.favorited_by.count())

    @admin.display(description='Количество добавлений в избранное')
    def favorites_total(self, obj):
        # used as a readonly field on the change form
        return obj.favorited_by.count()


# --- Favorite / ShoppingCart (register all models to allow edit/delete) -----

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    list_select_related = ('user', 'recipe')
    search_fields = (
        'user__email', 'user__username',
        'recipe__name', 'recipe__author__email', 'recipe__author__username'
    )
    autocomplete_fields = ('user', 'recipe')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    list_select_related = ('user', 'recipe')
    search_fields = (
        'user__email', 'user__username',
        'recipe__name', 'recipe__author__email', 'recipe__author__username'
    )
    autocomplete_fields = ('user', 'recipe')


# --- IngredientInRecipe (optional direct edit in admin menu) ----------------
@admin.register(IngredientInRecipe)
class IngredientInRecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'ingredient', 'amount')
    list_select_related = ('recipe', 'ingredient')
    search_fields = ('recipe__name', 'ingredient__name')
    autocomplete_fields = ('recipe', 'ingredient')
