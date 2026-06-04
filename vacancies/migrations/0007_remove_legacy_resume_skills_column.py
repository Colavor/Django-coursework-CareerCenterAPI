from django.db import migrations, connection


def drop_legacy_skills_column(apps, schema_editor):
    if connection.vendor != 'sqlite':
        return
    with connection.cursor() as cursor:
        cursor.execute('PRAGMA table_info(vacancies_resume)')
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        if 'skills' in columns and columns['skills'].upper() == 'TEXT':
            cursor.execute('ALTER TABLE vacancies_resume DROP COLUMN skills')


class Migration(migrations.Migration):

    dependencies = [
        ('vacancies', '0006_alter_resume_options_remove_application_created_at_and_more'),
    ]

    operations = [
        migrations.RunPython(drop_legacy_skills_column, migrations.RunPython.noop),
    ]
