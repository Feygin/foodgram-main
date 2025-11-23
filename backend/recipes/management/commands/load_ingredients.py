from recipes.models import Ingredient

from .base_load_from_json import BaseLoadFromJSONCommand


class Command(BaseLoadFromJSONCommand):
    model = Ingredient
    help = "Load ingredients from JSON file"
