# Generated manually
from django.db import migrations, models
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('vacancies', '0002_historicalapplication_historicalcompany_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Skill model - создаем ПЕРВЫМ, чтобы потом использовать в ManyToMany
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Название навыка')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
            ],
            options={
                'verbose_name': 'Навык',
                'verbose_name_plural': 'Навыки',
                'ordering': ['name'],
            },
        ),
        # Vacancy
        migrations.AddField(
            model_name='vacancy',
            name='created_by',
            field=models.ForeignKey(null=True, blank=True, on_delete=models.SET_NULL, related_name='created_vacancies', to=settings.AUTH_USER_MODEL, verbose_name='Создал'),
        ),
        migrations.AddField(
            model_name='vacancy',
            name='updated_by',
            field=models.ForeignKey(null=True, blank=True, on_delete=models.SET_NULL, related_name='updated_vacancies', to=settings.AUTH_USER_MODEL, verbose_name='Изменил'),
        ),
        # Student
        migrations.AddField(
            model_name='student',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Дата создания'),
        ),
        migrations.AddField(
            model_name='student',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Дата обновления'),
        ),
        # Company
        migrations.AddField(
            model_name='company',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Дата создания'),
        ),
        migrations.AddField(
            model_name='company',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Дата обновления'),
        ),
        # Resume
        migrations.AddField(
            model_name='resume',
            name='created_by',
            field=models.ForeignKey(null=True, blank=True, on_delete=models.SET_NULL, related_name='created_resumes', to=settings.AUTH_USER_MODEL, verbose_name='Создал'),
        ),
        migrations.AddField(
            model_name='resume',
            name='updated_by',
            field=models.ForeignKey(null=True, blank=True, on_delete=models.SET_NULL, related_name='updated_resumes', to=settings.AUTH_USER_MODEL, verbose_name='Изменил'),
        ),
        migrations.AddField(
            model_name='resume',
            name='skills_text',
            field=models.TextField(blank=True, verbose_name='Навыки (текст)'),
        ),
        migrations.AddField(
            model_name='resume',
            name='skills',
            field=models.ManyToManyField(blank=True, related_name='resumes', to='vacancies.skill', verbose_name='Навыки'),
        ),
        # Application
        migrations.AddField(
            model_name='application',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name='Дата создания'),
        ),
        migrations.AddField(
            model_name='application',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Дата обновления'),
        ),
    ]
