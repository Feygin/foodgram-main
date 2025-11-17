from django.contrib import admin
from django.db.models import Count

from .models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                     ShoppingCart, Tag)
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.safestring import mark_safe
from django.db.models import Exists, OuterRef

from .models import User, Subscription

class HasRecipesFilter(admin.SimpleListFilter):
    title = 'есть рецепты'
    parameter_name = 'has_recipes'

    def lookups(self, request, model_admin):
        return (('yes', 'Да'), ('no', 'Нет'))

    def queryset(self, request, queryset):
        from recipes.models import Recipe
        exists_qs = Recipe.objects.filter(author=OuterRef('pk'))
        if self.value() == 'yes':
            return queryset.annotate(has_recipes=Exists(exists_qs)).filter(has_recipes=True)
        if self.value() == 'no':
            return queryset.annotate(has_recipes=Exists(exists_qs)).filter(has_recipes=False)
        return queryset


class HasSubscriptionsFilter(admin.SimpleListFilter):
    title = 'есть подписки'
    parameter_name = 'has_subscriptions'

    def lookups(self, request, model_admin):
        return (('yes', 'Да'), ('no', 'Нет'))

    def queryset(self, request, queryset):
        exists_qs = Subscription.objects.filter(user=OuterRef('pk'))
        if self.value() == 'yes':
            return queryset.annotate(has_subs=Exists(exists_qs)).filter(has_subs=True)
        if self.value() == 'no':
            return queryset.annotate(has_subs=Exists(exists_qs)).filter(has_subs=False)
        return queryset


class HasSubscribersFilter(admin.SimpleListFilter):
    title = 'есть подписчики'
    parameter_name = 'has_subscribers'

    def lookups(self, request, model_admin):
        return (('yes', 'Да'), ('no', 'Нет'))

    def queryset(self, request, queryset):
        exists_qs = Subscription.objects.filter(author=OuterRef('pk'))
        if self.value() == 'yes':
            return queryset.annotate(has_followers=Exists(exists_qs)).filter(has_followers=True)
        if self.value() == 'no':
            return queryset.annotate(has_followers=Exists(exists_qs)).filter(has_followers=False)
        return queryset


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("username", "first_name", "last_name", "avatar")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "username", "first_name", "last_name", "password1", "password2"),
        }),
    )

    list_display = (
        "id",
        "username",
        "full_name",
        "email",
        "avatar_preview",
        "recipes_count",
        "subscriptions_count",
        "subscribers_count",
        "is_staff",
    )
    list_filter = (
        HasRecipesFilter,
        HasSubscriptionsFilter,
        HasSubscribersFilter,
        "is_staff",
        "is_superuser",
        "is_active",
        "groups",
    )
    search_fields = ("email", "username", "first_name", "last_name")
    ordering = ("id",)

    @admin.display(description="ФИО")
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    @admin.display(description="Аватар")
    def avatar_preview(self, obj):
        if getattr(obj, "avatar", None):
            try:
                url = obj.avatar.url
                return mark_safe(
                    f'<img src="{url}" width="48" height="48" '
                    f'style="border-radius:50%;object-fit:cover" />'
                )
            except Exception:
                pass
        return "—"

    @admin.display(description="Рецептов")
    def recipes_count(self, obj):
        from recipes.models import Recipe
        return Recipe.objects.filter(author=obj).count()

    @admin.display(description="Подписок")
    def subscriptions_count(self, obj):
        return Subscription.objects.filter(user=obj).count()

    @admin.display(description="Подписчиков")
    def subscribers_count(self, obj):
        return Subscription.objects.filter(author=obj).count()


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "author")
    search_fields = (
        "user__email",
        "user__username",
        "author__email",
        "author__username",
    )
    list_select_related = ("user", "author")

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
