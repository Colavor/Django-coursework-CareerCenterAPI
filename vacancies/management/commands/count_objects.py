from django.core.management.base import BaseCommand
from vacancies.models import Vacancy, Student, Company, Resume, Application, Skill


class Command(BaseCommand):
    help = 'Выводит количество объектов в базе данных'

    def handle(self, *args, **options):
        vacancy_count = Vacancy.objects.count()
        student_count = Student.objects.count()
        company_count = Company.objects.count()
        resume_count = Resume.objects.count()
        application_count = Application.objects.count()
        skill_count = Skill.objects.count()

        self.stdout.write(self.style.SUCCESS(f'Вакансий: {vacancy_count}'))
        self.stdout.write(self.style.SUCCESS(f'Студентов: {student_count}'))
        self.stdout.write(self.style.SUCCESS(f'Компаний: {company_count}'))
        self.stdout.write(self.style.SUCCESS(f'Резюме: {resume_count}'))
        self.stdout.write(self.style.SUCCESS(f'Заявок: {application_count}'))
        self.stdout.write(self.style.SUCCESS(f'Навыков: {skill_count}'))

        total = vacancy_count + student_count + company_count + resume_count + application_count + skill_count
        self.stdout.write(self.style.WARNING(f'Всего объектов: {total}'))
