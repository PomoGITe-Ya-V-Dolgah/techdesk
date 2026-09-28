from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from service.importers import import_equipment


class Command(BaseCommand):
    help = "Импорт реестра оборудования из .xlsx или .csv: python manage.py import_equipment реестр.xlsx"

    def add_arguments(self, parser):
        parser.add_argument("path")

    def handle(self, *args, path, **options):
        file = Path(path)
        if not file.exists():
            raise CommandError(f"Файл не найден: {file}")
        result = import_equipment(file.name, file.read_bytes())
        for line, message in result.warnings:
            self.stdout.write(self.style.WARNING(f"Строка {line}: {message}"))
        for line, message in result.errors:
            self.stdout.write(self.style.ERROR(f"Строка {line}: {message}"))
        self.stdout.write(self.style.SUCCESS(f"Добавлено: {result.created}, обновлено: {result.updated}, ошибок: {len(result.errors)}"))
