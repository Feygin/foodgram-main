from django.contrib import admin
from django.db.models import Count, Exists, OuterRef
from django.utils.safestring import mark_safe

from .models import (
    Favorite,
    Ingredient,
    IngredientInRecipe,
    Recipe,
    ShoppingCart,
    Subscription,
    Tag,
    User,
)


class BaseExistsFilter(admin.SimpleListFilter):
    YES_NO = (("yes", "Да"), ("no", "Нет"))

    title = None
    parameter_name = None
    related_field = None
    exists_model = None
    annotate_field = None

    def lookups(self, request, model_admin):
        return self.YES_NO

    def queryset(self, request, queryset):
        value = self.value()
        if value not in ("yes", "no"):
            return queryset

        exists_qs = self.exists_model.objects.filter(
            **{self.related_field: OuterRef("pk")}
        )

        queryset = queryset.annotate(
            **{self.annotate_field: Exists(exists_qs)})

        return queryset.filter(**{self.annotate_field: value == "yes"})


class HasRecipesFilter(BaseExistsFilter):
    title = "есть рецепты"
    parameter_name = "has_recipes"
    related_field = "author"
    exists_model = Recipe
    annotate_field = "has_recipes"


class HasSubscriptionsFilter(BaseExistsFilter):
    title = "есть подписки"
    parameter_name = "has_subscriptions"
    related_field = "user"
    exists_model = Subscription
    annotate_field = "has_subs"


class HasSubscribersFilter(BaseExistsFilter):
    title = "есть подписчики"
    parameter_name = "has_subscribers"
    related_field = "author"
    exists_model = Subscription
    annotate_field = "has_followers"


# ------------------------
#  Admin
# ------------------------


class BaseRecipeRelationAdmin(admin.ModelAdmin):

    @admin.display(description="Рецептов")
    def recipes_count(self, obj):
        return obj.recipes.count()


@admin.register(User)
class UserAdmin(BaseRecipeRelationAdmin):
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Персональная информация",
            {"fields": ("username", "first_name", "last_name", "avatar")},
        ),
        (
            "Права",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
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
    )

    list_filter = (
        HasRecipesFilter,
        HasSubscriptionsFilter,
        HasSubscribersFilter,
        "is_staff",
        "is_superuser",
        "is_active",
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
            return (
                f'<img src="{user.avatar.url}" width="48" height="48" '
                'style="border-radius:50%;object-fit:cover;">'
            )
        return "—"

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


class IngredientInRecipeInline(admin.TabularInline):
    model = IngredientInRecipe
    extra = 0
    autocomplete_fields = ("ingredient",)
    min_num = 1


@admin.register(Tag)
class TagAdmin(BaseRecipeRelationAdmin):

    list_display = ("id", "name", "slug", "recipes_count")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("name",)


@admin.register(Ingredient)
class IngredientAdmin(BaseRecipeRelationAdmin):

    list_display = ("id", "name", "measurement_unit", "recipes_count")
    search_fields = ("name", "measurement_unit")
    ordering = ("name",)


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
    list_filter = ("tags", "author")
    autocomplete_fields = ("tags",)
    inlines = (IngredientInRecipeInline,)
    readonly_fields = (
        "favorites_count",
        "image_preview",
        "ingredients_html",
        "tags_html",
    )

    fields = (
        ("name", "author"),
        "image",
        "image_preview",
        "text",
        "cooking_time",
        "tags",
        "ingredients_html",
        "tags_html",
        "favorites_count",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(_fav_count=Count("favorites"))

    @admin.display(description="Всего добавлений в избранное")
    def favorites_count(self, recipe):
        return getattr(recipe, "_fav_count", recipe.favorites.count())

    @admin.display(description="Продукты")
    @mark_safe
    def ingredients_html(self, recipe):
        items = recipe.recipe_ingredients.select_related("ingredient")
        return "<br>".join(
            (f"{item.ingredient.name} — {item.amount} "
             f"{item.ingredient.measurement_unit}")
            for item in items
        )

    @admin.display(description="Теги")
    @mark_safe
    def tags_html(self, recipe):
        return "<br>".join(tag.name for tag in recipe.tags.all())

    @admin.display(description="Картинка")
    @mark_safe
    def image_preview(self, recipe):
        return (
            f'<img src="{recipe.image.url}" '
            'width="80" height="80" '
            'style="object-fit:cover;border-radius:6px;">'
        )


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


@admin.register(IngredientInRecipe)
class IngredientInRecipeAdmin(admin.ModelAdmin):
    list_display = ("id", "recipe", "ingredient", "amount")
    list_select_related = ("recipe", "ingredient")
    search_fields = ("recipe__name", "ingredient__name")
    autocomplete_fields = ("recipe", "ingredient")
