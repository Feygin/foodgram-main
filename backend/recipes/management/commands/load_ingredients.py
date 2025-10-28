import json
from django.core.management.base import BaseCommand
from recipes.models import Ingredient

class Command(BaseCommand):
    help = 'Load ingredients from JSON file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to JSON file with ingredients')

    def handle(self, *args, **options):
        file_path = options['file_path']
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        created_count = 0
        for item in data:
            _, created = Ingredient.objects.get_or_create(
                name=item['name'],
                measurement_unit=item['measurement_unit']
            )
            if created:
                created_count += 1

        self.stdout.write(self.style.SUCCESS(f'✅ Loaded {created_count} ingredients.'))
