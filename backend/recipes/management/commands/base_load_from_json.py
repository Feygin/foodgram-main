import json

from django.core.management.base import BaseCommand, CommandError


class BaseLoadFromJSONCommand(BaseCommand):
    """
    Общий алгоритм загрузки JSON → модель.
    Использует bulk_create, принимает модель и список полей уникальности.
    """

    model = None

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str, help="Path to JSON file")

    def handle(self, *args, **options):
        try:
            file_path = options["file_path"]

            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            objects = [self.model(**item) for item in data]

            created = self.model.objects.bulk_create(
                objects,
                ignore_conflicts=True
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Loaded {len(created)} objects from {file_path}")
            )

        except Exception as error:
            raise CommandError(f"Error while loading {file_path}: {error}")
