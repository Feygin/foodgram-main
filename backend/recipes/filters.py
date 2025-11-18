import django_filters
from .models import Recipe, Ingredient
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

class IngredientFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(
        field_name="name",
        lookup_expr="istartswith"
    )

    class Meta:
        model = Ingredient
        fields = ("name",)

class RecipeFilter(django_filters.FilterSet):
    tags = django_filters.AllValuesMultipleFilter(field_name="tags__slug")
    author = django_filters.NumberFilter(field_name="author_id")

    # Меняем BooleanFilter → NumberFilter
    is_in_shopping_cart = django_filters.NumberFilter(method="filter_in_cart")
    is_favorited = django_filters.NumberFilter(method="filter_fav")

    def filter_in_cart(self, queryset, name, value):
        user = self.request.user

        # value приходит как int: 0 или 1
        if value != 1 or user.is_anonymous:
            return queryset

        return queryset.filter(shopping_cart__user=user)

    def filter_fav(self, queryset, name, value):
        user = self.request.user

        if value != 1 or user.is_anonymous:
            return queryset

        return queryset.filter(favorites__user=user)

    class Meta:
        model = Recipe
        fields = ("tags", "author", "is_in_shopping_cart", "is_favorited")

