# Generated manually to update historical tables
from django.db import migrations, models
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('vacancies', '0003_add_fields'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Update HistoricalCompany
        migrations.AddField(
            model_name='historicalcompany',
            name='created_at',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, editable=False, verbose_name='Дата создания'),
        ),
        migrations.AddField(
            model_name='historicalcompany',
            name='updated_at',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, editable=False, verbose_name='Дата обновления'),
        ),
        # Update HistoricalStudent
        migrations.AddField(
            model_name='historicalstudent',
            name='created_at',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, editable=False, verbose_name='Дата создания'),
        ),
        migrations.AddField(
            model_name='historicalstudent',
            name='updated_at',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, editable=False, verbose_name='Дата обновления'),
        ),
        # Update HistoricalApplication
        migrations.AddField(
            model_name='historicalapplication',
            name='created_at',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, editable=False, verbose_name='Дата создания'),
        ),
        migrations.AddField(
            model_name='historicalapplication',
            name='updated_at',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, editable=False, verbose_name='Дата обновления'),
        ),
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
