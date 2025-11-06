from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.db.models import Exists, OuterRef

from .models import User, Subscription

class HasRecipesFilter(admin.SimpleListFilter):
    title = _('есть рецепты')
    parameter_name = 'has_recipes'

    def lookups(self, request, model_admin):
        return (('yes', _('Да')), ('no', _('Нет')))

    def queryset(self, request, queryset):
        from recipes.models import Recipe
        exists_qs = Recipe.objects.filter(author=OuterRef('pk'))
        if self.value() == 'yes':
            return queryset.annotate(has_recipes=Exists(exists_qs)).filter(has_recipes=True)
        if self.value() == 'no':
            return queryset.annotate(has_recipes=Exists(exists_qs)).filter(has_recipes=False)
        return queryset


class HasSubscriptionsFilter(admin.SimpleListFilter):
    title = _('есть подписки')
    parameter_name = 'has_subscriptions'

    def lookups(self, request, model_admin):
        return (('yes', _('Да')), ('no', _('Нет')))

    def queryset(self, request, queryset):
        exists_qs = Subscription.objects.filter(user=OuterRef('pk'))
        if self.value() == 'yes':
            return queryset.annotate(has_subs=Exists(exists_qs)).filter(has_subs=True)
        if self.value() == 'no':
            return queryset.annotate(has_subs=Exists(exists_qs)).filter(has_subs=False)
        return queryset


class HasSubscribersFilter(admin.SimpleListFilter):
    title = _('есть подписчики')
    parameter_name = 'has_subscribers'

    def lookups(self, request, model_admin):
        return (('yes', _('Да')), ('no', _('Нет')))

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
        (_("Personal info"), {"fields": ("username", "first_name", "last_name", "avatar")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
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

    @admin.display(description=_("ФИО"))
    def full_name(self, obj):
        """Return user's full name (first + last)."""
        return f"{obj.first_name} {obj.last_name}"

    @admin.display(description=_("Аватар"))
    def avatar_preview(self, obj):
        if getattr(obj, "avatar", None):
            try:
                url = obj.avatar.url
                return mark_safe(f'<img src="{url}" width="48" height="48" '
                                 f'style="border-radius:50%;object-fit:cover" />')
            except Exception:
                pass
        return "—"

    @admin.display(description=_("Рецептов"))
    def recipes_count(self, obj):
        from recipes.models import Recipe
        return Recipe.objects.filter(author=obj).count()

    @admin.display(description=_("Подписок"))
    def subscriptions_count(self, obj):
        return Subscription.objects.filter(user=obj).count()

    @admin.display(description=_("Подписчиков"))
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
