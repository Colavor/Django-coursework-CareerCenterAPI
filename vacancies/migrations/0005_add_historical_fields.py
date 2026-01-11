# Generated manually to add missing fields to historical tables
from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('vacancies', '0004_update_historical_tables'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Update HistoricalVacancy - добавить created_by и updated_by
        migrations.AddField(
            model_name='historicalvacancy',
            name='created_by',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=models.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Создал'),
        ),
        migrations.AddField(
            model_name='historicalvacancy',
            name='updated_by',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=models.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Изменил'),
        ),
        # Update HistoricalResume - добавить created_by, updated_by, skills_text
        migrations.AddField(
            model_name='historicalresume',
            name='created_by',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=models.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Создал'),
        ),
        migrations.AddField(
            model_name='historicalresume',
            name='updated_by',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=models.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='Изменил'),
        ),
        migrations.AddField(
            model_name='historicalresume',
            name='skills_text',
            field=models.TextField(blank=True, verbose_name='Навыки (текст)'),
        ),
    ]
