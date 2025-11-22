from recipes.management.commands.base_load_from_json import (
    BaseLoadFromJSONCommand,
)
from recipes.models import Tag


class Command(BaseLoadFromJSONCommand):
    model = Tag
    help = "Load tags from JSON file"
