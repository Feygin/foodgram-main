from recipes.models import Tag
from recipes.management.commands.base_load_from_json import BaseLoadFromJSONCommand


class Command(BaseLoadFromJSONCommand):
    model = Tag
    fields_for_unique_lookup = ("slug",)
    help = "Load tags from JSON file"
