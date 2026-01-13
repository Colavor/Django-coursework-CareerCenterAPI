from django.core.management.base import BaseCommand
from vacancies.models import Application


class Command(BaseCommand):
    help = 'Выводит статистику по заявкам'

    def handle(self, *args, **options):
        total = Application.objects.count()

        self.stdout.write(self.style.SUCCESS(f'Всего заявок: {total}'))

        for status_code, status_name in Application.STATUS_CHOICES:
            count = Application.objects.filter(status=status_code).count()
            self.stdout.write(self.style.SUCCESS(f'{status_name}: {count}'))
