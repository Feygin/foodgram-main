from django.contrib import admin
from django.db.models import Count, Exists, OuterRef
from django.utils.safestring import mark_safe

from .models import (
    User,
    Subscription,
    Tag,
    Ingredient,
    IngredientInRecipe,
    Recipe,
    Favorite,
    ShoppingCart,
)


# ------------------------
#  Custom Admin Filters
# ------------------------

class HasRecipesFilter(admin.SimpleListFilter):
    title = "есть рецепты"
    parameter_name = "has_recipes"

    def lookups(self, request, model_admin):
        return (("yes", "Да"), ("no", "Нет"))

    def queryset(self, request, queryset):
        exists_qs = Recipe.objects.filter(author=OuterRef("pk"))
        queryset = queryset.annotate(has_recipes=Exists(exists_qs))
        if self.value() == "yes":
            return queryset.filter(has_recipes=True)
        if self.value() == "no":
            return queryset.filter(has_recipes=False)
        return queryset


class HasSubscriptionsFilter(admin.SimpleListFilter):
    title = "есть подписки"
    parameter_name = "has_subscriptions"

    def lookups(self, request, model_admin):
        return (("yes", "Да"), ("no", "Нет"))

    def queryset(self, request, queryset):
        exists_qs = Subscription.objects.filter(user=OuterRef("pk"))
        queryset = queryset.annotate(has_subs=Exists(exists_qs))
        if self.value() == "yes":
            return queryset.filter(has_subs=True)
        if self.value() == "no":
            return queryset.filter(has_subs=False)
        return queryset


class HasSubscribersFilter(admin.SimpleListFilter):
    title = "есть подписчики"
    parameter_name = "has_subscribers"

    def lookups(self, request, model_admin):
        return (("yes", "Да"), ("no", "Нет"))

    def queryset(self, request, queryset):
        exists_qs = Subscription.objects.filter(author=OuterRef("pk"))
        queryset = queryset.annotate(has_followers=Exists(exists_qs))
        if self.value() == "yes":
            return queryset.filter(has_followers=True)
        if self.value() == "no":
            return queryset.filter(has_followers=False)
        return queryset


# ------------------------
#  User Admin
# ------------------------

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Персональная информация", {"fields": ("username", "first_name", "last_name", "avatar")}),
        ("Права", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Важные даты", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
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
    def full_name(self, user):
        return f"{user.first_name} {user.last_name}"

    @admin.display(description="Аватар")
    @mark_safe
    def avatar_preview(self, user):
        if getattr(user, "avatar", None):
            try:
                return f'<img src="{user.avatar.url}" width="48" height="48" style="border-radius:50%;object-fit:cover;">'
            except Exception:
                pass
        return "—"

    @admin.display(description="Рецептов")
    def recipes_count(self, user):
        return Recipe.objects.filter(author=user).count()

    @admin.display(description="Подписок")
    def subscriptions_count(self, user):
        return Subscription.objects.filter(user=user).count()

    @admin.display(description="Подписчиков")
    def subscribers_count(self, user):
        return Subscription.objects.filter(author=user).count()


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


# ------------------------
#  Inline Models
# ------------------------

class IngredientInRecipeInline(admin.TabularInline):
    model = IngredientInRecipe
    extra = 0
    autocomplete_fields = ("ingredient",)
    min_num = 1


# ------------------------
#  Tag Admin
# ------------------------

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "recipes_count")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)

    @admin.display(description="Рецептов")
    def recipes_count(self, tag):
        return tag.recipes.count()


# ------------------------
#  Ingredient Admin
# ------------------------

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "measurement_unit", "recipes_count")
    search_fields = ("name", "measurement_unit")
    ordering = ("name",)

    @admin.display(description="Рецептов")
    def recipes_count(self, ingredient):
        return ingredient.recipe_ingredients.count()


# ------------------------
#  Recipe Admin (big changes)
# ------------------------

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "cooking_time",
        "author",
        "favorites_count",
        "ingredients_html",
        "tags_html",
        "image_preview",
    )

    list_select_related = ("author",)
    search_fields = (
        "name",
        "author__username",
        "author__email",
        "author__first_name",
        "author__last_name",
    )
    list_filter = ("tags",)
    autocomplete_fields = ("tags",)
    inlines = (IngredientInRecipeInline,)
    readonly_fields = (
        "favorites_total",
        "image_preview_admin",
        "ingredients_html",
        "tags_html",
    )

    fields = (
        ("name", "author"),
        "image",
        "image_preview_admin",
        "text",
        "cooking_time",
        "tags",
        "ingredients_html",
        "tags_html",
        "favorites_total",
    )

    # Prefetch favorites count
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_fav_count=Count("favorite"))

    # Favorites count in list_display
    @admin.display(description="В избранном", ordering="_fav_count")
    def favorites_count(self, recipe):
        return getattr(recipe, "_fav_count", recipe.favorite.count())

    @admin.display(description="Всего добавлений в избранное")
    def favorites_total(self, recipe):
        return recipe.favorite.count()

    # Ingredients HTML list
    @admin.display(description="Продукты")
    @mark_safe
    def ingredients_html(self, recipe):
        items = recipe.recipe_ingredients.select_related("ingredient")
        html = "<ul>"
        for item in items:
            html += (
                f"<li>{item.ingredient.name} — "
                f"{item.amount} {item.ingredient.measurement_unit}</li>"
            )
        html += "</ul>"
        return html

    # Tags HTML list
    @admin.display(description="Теги")
    @mark_safe
    def tags_html(self, recipe):
        html = ", ".join(f"<span>{tag.name}</span>" for tag in recipe.tags.all())
        return html or "—"

    # Image preview
    @admin.display(description="Картинка")
    @mark_safe
    def image_preview(self, recipe):
        try:
            return (
                f'<img src="{recipe.image.url}" '
                f'width="80" height="80" style="object-fit:cover;border-radius:6px;">'
            )
        except Exception:
            return "—"

    @admin.display(description="Превью изображения")
    @mark_safe
    def image_preview_admin(self, recipe):
        return self.image_preview(recipe)


# ------------------------
#  Favorite and ShoppingCart (merged registration)
# ------------------------

@admin.register(Favorite, ShoppingCart)
class UserRecipeRelationAdmin(admin.ModelAdmin):
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


# ------------------------
#  IngredientInRecipe Admin
# ------------------------

@admin.register(IngredientInRecipe)
class IngredientInRecipeAdmin(admin.ModelAdmin):
    list_display = ("id", "recipe", "ingredient", "amount")
    list_select_related = ("recipe", "ingredient")
    search_fields = ("recipe__name", "ingredient__name")
    autocomplete_fields = ("recipe", "ingredient")
