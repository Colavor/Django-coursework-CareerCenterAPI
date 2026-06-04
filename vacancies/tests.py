"""
Тесты приложения vacancies: модели, сериализаторы, REST API.

Покрывают валидацию бизнес-логики, права доступа, фильтрацию и shortlist.
"""

from __future__ import annotations

from datetime import date

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APITestCase, APIRequestFactory

from .models import Student, Company, Vacancy, Resume, Application
from .serializers import VacancySerializers, ReviewSerializers


class VacancyModelTest(TestCase):
    """Тесты валидации модели Vacancy на уровне clean/full_clean."""

    def setUp(self) -> None:
        """Создать компанию-работодателя для привязки вакансий."""
        self.company = Company.objects.create(
            name='Test Co', email='test@co.ru', industry='IT'
        )

    def test_vacancy_salary_must_be_positive(self) -> None:
        """
        Зарплата 0 при full_clean() вызывает ValidationError.

        Проверяет правило БЛ: зарплата должна быть положительной (models.Vacancy.clean).
        """
        vacancy = Vacancy(
            company=self.company,
            title='Dev',
            description='desc',
            salary=0,
            status='active',
        )
        with self.assertRaises(ValidationError):
            vacancy.full_clean()


class ReviewSerializerTest(TestCase):
    """Тесты валидации ReviewSerializers (отзыв только после заявки)."""

    def setUp(self) -> None:
        """Создать студента, пользователя и компанию без заявки."""
        self.user = User.objects.create_user(
            username='student', password='pass', email='st@test.ru'
        )
        self.student = Student.objects.create(
            first_name='Ann', last_name='Lee', email='st@test.ru',
            birth_date=date(2004, 5, 5), specialty='IT',
        )
        self.company = Company.objects.create(
            name='Co', email='c@co.ru', industry='IT'
        )

    def test_review_fails_without_application(self) -> None:
        """
        Отзыв без заявки в компанию не проходит валидацию сериализатора.

        Ожидается ошибка non_field_errors с текстом про необходимость заявки.
        """
        request = APIRequestFactory().post('/api/reviews/create/')
        request.user = self.user
        serializer = ReviewSerializers(
            data={'company_id': self.company.id, 'rating': 5, 'text': 'Хорошая компания'},
            context={'request': request},
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn(
            'Отзыв можно оставить только о компании, на вакансию которой вы подавали заявку.',
            serializer.errors['non_field_errors'],
        )


class VacancyAPITest(APITestCase):
    """Тесты публичного API каталога вакансий и django-filter."""

    def setUp(self) -> None:
        """Создать две вакансии у разных компаний для списка и фильтра."""
        self.it_company = Company.objects.create(
            name='IT Co', email='it@co.ru', industry='IT'
        )
        self.bank_company = Company.objects.create(
            name='Bank', email='bank@co.ru', industry='Finance'
        )
        self.vacancy_it = Vacancy.objects.create(
            company=self.it_company,
            title='Python Developer',
            description='backend',
            salary=80000,
            status='active',
        )
        self.vacancy_bank = Vacancy.objects.create(
            company=self.bank_company,
            title='Analyst',
            description='finance',
            salary=60000,
            status='active',
        )

    def test_vacancy_list_returns_vacancies(self) -> None:
        """
        GET /api/vacancies/ возвращает 200 и обе вакансии в results.

        Проверяет доступность каталога (IsAdminOrReadOnly — чтение без авторизации).
        """
        response: Response = self.client.get('/api/vacancies/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_filter_vacancies_by_company_industry(self) -> None:
        """
        Фильтр ?company=<id> оставляет только вакансии выбранной компании.

        Проверяет DjangoFilterBackend и filterset_fields на VacancyViewSet.
        """
        response: Response = self.client.get(f'/api/vacancies/?company={self.it_company.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Python Developer')


class ShortlistAPITest(APITestCase):
    """Тесты shortlist студента (сессия + action add_to_shortlist)."""

    def setUp(self) -> None:
        """Создать студента, пользователя и активную вакансию."""
        self.user = User.objects.create_user(
            username='student', password='pass', email='st@test.ru'
        )
        self.student = Student.objects.create(
            first_name='Ann', last_name='Ann', email='st@test.ru',
            birth_date=date(2004, 5, 5), specialty='IT',
        )
        company = Company.objects.create(name='Co', email='c@co.ru', industry='IT')
        self.vacancy = Vacancy.objects.create(
            company=company, title='Dev', description='d',
            salary=50000, status='active',
        )

    def test_add_vacancy_to_shortlist(self) -> None:
        """
        POST add_to_shortlist добавляет id вакансии в shortlist сессии студента.

        Требуется IsStudent (force_authenticate) и пустой shortlist в session.
        """
        self.client.force_authenticate(user=self.user)
        session = self.client.session
        session[f'shortlist_{self.student.id}'] = []
        session.save()

        url = f'/api/vacancies/{self.vacancy.id}/add_to_shortlist/'
        response: Response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(self.vacancy.id, response.data['shortlist'])


class ApplicationAPITest(APITestCase):
    """Тесты API заявок: создание, валидация, права IsAdminOrApplicationOwner."""

    def setUp(self) -> None:
        """Подготовить студента, резюме, активную и закрытую вакансии, одну заявку."""
        self.user = User.objects.create_user(
            username='student', password='pass', email='st@test.ru'
        )
        self.student = Student.objects.create(
            first_name='Ann', last_name='Lee', email='st@test.ru',
            birth_date=date(2004, 5, 5), specialty='IT',
        )
        company = Company.objects.create(name='Co', email='c@co.ru', industry='IT')
        self.vacancy = Vacancy.objects.create(
            company=company, title='Dev', description='d',
            requirements='python', salary=50000, status='active',
        )
        self.closed_vacancy = Vacancy.objects.create(
            company=company, title='Old', description='d',
            salary=40000, status='closed',
        )
        self.resume = Resume.objects.create(
            student=self.student, experience='exp', contacts='mail',
            skills_text='Python', status='active',
        )
        self.application = Application.objects.create(
            student=self.student,
            vacancy=self.vacancy,
            resume=self.resume,
            employer_comment='-',
        )
        self.client.force_authenticate(user=self.user)

    def test_create_application(self) -> None:
        """
        POST /api/applications/ создаёт заявку со статусом sent.

        Студент подаёт заявку на вторую активную вакансию с активным резюме.
        """
        vacancy2 = Vacancy.objects.create(
            company=self.vacancy.company, title='Dev 2', description='d',
            salary=55000, status='active',
        )
        response: Response = self.client.post('/api/applications/', {
            'student': self.student.id,
            'vacancy': vacancy2.id,
            'resume': self.resume.id,
            'employer_comment': '-',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'sent')

    def test_application_on_closed_vacancy_fails(self) -> None:
        """
        Заявка на закрытую вакансию возвращает 400.

        Проверяет ApplicationSerializers.validate (вакансия должна быть active).
        """
        response: Response = self.client.post('/api/applications/', {
            'student': self.student.id,
            'vacancy': self.closed_vacancy.id,
            'resume': self.resume.id,
            'employer_comment': '-',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_application_retrieve_forbidden_for_other_student(self) -> None:
        """
        GET чужой заявки возвращает 403.

        Проверяет IsAdminOrApplicationOwner на retrieve ApplicationViewSet.
        """
        other_user = User.objects.create_user(
            username='other', password='pass', email='other@test.ru'
        )
        Student.objects.create(
            first_name='Other', last_name='User', email='other@test.ru',
            birth_date=date(2004, 1, 1), specialty='IT',
        )
        self.client.force_authenticate(user=other_user)
        response: Response = self.client.get(f'/api/applications/{self.application.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_application_fails(self) -> None:
        """
        Повторная заявка student+vacancy возвращает 400.

        Проверяет уникальность пары студент–вакансия в ApplicationSerializers.
        """
        response: Response = self.client.post('/api/applications/', {
            'student': self.student.id,
            'vacancy': self.vacancy.id,
            'resume': self.resume.id,
            'employer_comment': '-',
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SerializerTest(TestCase):
    """Тесты сериализаторов VacancySerializers (валидация и context)."""

    def setUp(self) -> None:
        """Создать компанию для данных сериализатора вакансии."""
        self.company = Company.objects.create(
            name='Co', email='c@co.ru', industry='IT'
        )

    def test_vacancy_serializer_invalid_salary(self) -> None:
        """
        Отрицательная зарплата в данных сериализатора даёт ошибку поля salary.

        Проверяет validate_salary в VacancySerializers.
        """
        serializer = VacancySerializers(data={
            'company': self.company.id,
            'title': 'Dev',
            'description': 'desc',
            'salary': -100,
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('salary', serializer.errors)

    def test_is_favorite_from_context(self) -> None:
        """
        is_favorite=True, если id вакансии передан в context favorite_vacancies.

        Проверяет SerializerMethodField get_is_favorite и передачу через context.
        """
        vacancy = Vacancy.objects.create(
            company=self.company, title='Dev', description='d',
            salary=50000, status='active',
        )
        serializer = VacancySerializers(
            vacancy,
            context={'favorite_vacancies': [vacancy.id]},
        )
        self.assertTrue(serializer.data['is_favorite'])
