import json

from django.core.management.base import BaseCommand, CommandError


class BaseLoadFromJSONCommand(BaseCommand):
    """
    Общий алгоритм загрузки JSON → модель.
    Использует bulk_create, принимает модель и список полей уникальности.
    """

    model = None
    fields_for_unique_lookup = ()

    def add_arguments(self, parser):
        parser.add_argument("file_path", type=str, help="Path to JSON file")

    def handle(self, *args, **options):
        try:
            file_path = options["file_path"]

            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)

            objects = []
            existing = set(
                self.model.objects.values_list(*self.fields_for_unique_lookup)
            )

            for item in data:
                key = tuple(
                    item[field] for field in self.fields_for_unique_lookup)
                if key in existing:
                    continue
                existing.add(key)

                objects.append(self.model(**item))

            created = self.model.objects.bulk_create(objects)

            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Loaded {len(created)} objects from {file_path}")
            )

        except Exception as error:
            raise CommandError(error)
