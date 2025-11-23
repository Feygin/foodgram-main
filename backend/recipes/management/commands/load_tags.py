from recipes.models import Tag

from .base_load_from_json import BaseLoadFromJSONCommand


class Command(BaseLoadFromJSONCommand):
    model = Tag
    help = "Load tags from JSON file"
