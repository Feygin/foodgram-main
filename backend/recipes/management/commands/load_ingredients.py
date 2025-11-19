from recipes.management.commands.base_load_from_json import \
    BaseLoadFromJSONCommand
from recipes.models import Ingredient


class Command(BaseLoadFromJSONCommand):
    model = Ingredient
    fields_for_unique_lookup = ("name", "measurement_unit")
    help = "Load ingredients from JSON file"
