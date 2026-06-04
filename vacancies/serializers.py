from __future__ import annotations

from typing import Any

from rest_framework import serializers

from .models import Student, Company, Vacancy, Resume, Application


class VacancySerializers(serializers.ModelSerializer):
    """Сериализатор вакансии с аннотациями и флагом shortlist."""

    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all())
    is_favorite = serializers.SerializerMethodField()
    applications_count = serializers.IntegerField(read_only=True)
    shortlist_count = serializers.IntegerField(read_only=True)
    company_avg_rating = serializers.FloatField(read_only=True)

    class Meta:
        model = Vacancy
        fields = [
            'id', 'company', 'title', 'requirements', 'description',
            'salary', 'employment_type', 'schedule',
            'location', 'published_at', 'closed_at',
            'status', 'created_at', 'updated_at',
            'is_favorite', 'applications_count', 'shortlist_count', 'company_avg_rating',
        ]

        read_only_fields = ['created_at', 'updated_at']

    def get_is_favorite(self, obj: Vacancy) -> bool:
        """
        Вакансия в shortlist текущего студента (из context).

        Args:
            obj: Объект вакансии.
        """
        favorite_vacancies = self.context.get('favorite_vacancies', [])
        return obj.id in favorite_vacancies

    def validate_salary(self, value: int | None) -> int:
        """Зарплата должна быть положительной."""
        if value is None or value <= 0:
            raise serializers.ValidationError('Зарплата должна быть положительным числом')
        return value

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Дата закрытия не раньше даты публикации."""
        if 'published_at' in data:
            published = data['published_at']
        else:
            published = getattr(self.instance, 'published_at', None)

        if 'closed_at' in data:
            closed = data['closed_at']
        else:
            closed = getattr(self.instance, 'closed_at', None)

        if closed and published and closed < published:
            raise serializers.ValidationError({'closed_at': 'Дата закрытия не может быть раньше даты публикации'})
        return data


class StudentSerializers(serializers.ModelSerializer):
    """Сериализатор профиля студента."""

    class Meta:
        model = Student
        fields = [
            'id', 'first_name', 'last_name', 'email',
            'phone', 'birth_date', 'course', 'specialty',
            'group', 'faculty', 'photo'
        ]

    def validate_course(self, value: int) -> int:
        """Курс обучения от 1 до 6."""
        if value < 1 or value > 6:
            raise serializers.ValidationError('Курс должен быть в диапазоне от 1 до 6')
        return value


class CompanySerializers(serializers.ModelSerializer):
    """Сериализатор компании-работодателя."""

    class Meta:
        model = Company
        fields = [
            'id', 'name', 'description', 'website',
            'email', 'phone', 'industry', 'address',
            'logo', 'size'
        ]


class ResumeSerializers(serializers.ModelSerializer):
    """Сериализатор резюме студента."""

    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all())

    class Meta:
        model = Resume
        fields = [
            'id', 'student', 'title', 'experience',
            'education', 'achievements', 'contacts',
            'status', 'skills_text', 'skills'
        ]


class ApplicationSerializers(serializers.ModelSerializer):
    """Сериализатор заявки на вакансию с бизнес-валидацией."""

    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all())
    vacancy = serializers.PrimaryKeyRelatedField(queryset=Vacancy.objects.all())
    resume = serializers.PrimaryKeyRelatedField(queryset=Resume.objects.all())

    class Meta:
        model = Application
        fields = [
            'id', 'student', 'vacancy', 'resume',
            'cover_letter', 'submitted_at', 'status',
            'response_date', 'employer_comment'
        ]

        read_only_fields = ['submitted_at']

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Проверка заявки: резюме, активная вакансия, без дубликата.

        Args:
            data: Поля заявки из запроса.
        """
        student = data.get('student')
        resume = data.get('resume')
        vacancy = data.get('vacancy')

        if resume is None:
            raise serializers.ValidationError({'resume': 'Для подачи заявки заполните резюме'})

        if resume.student_id != student.id:
            raise serializers.ValidationError({'resume': 'Резюме принадлежит другому студенту'})

        if resume.status != 'active':
            raise serializers.ValidationError({'resume': 'Для подачи заявки требуется активное резюме.'})

        existing = Application.objects.filter(student=student, vacancy=vacancy)
        if self.instance:
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError(
                'Вы уже подавали заявку на эту вакансию.'
            )

        if vacancy.status != 'active':
            raise serializers.ValidationError({
                'vacancy': 'Вакансия недоступна для отклика (не активна).'
            })

        request = self.context.get('request')
        if request and request.user.is_authenticated and not request.user.is_staff:
            from .permissions import get_user_student
            user_student = get_user_student(request.user)
            if user_student and student.id != user_student.id:
                raise serializers.ValidationError({'student': 'Нельзя подать заявку за другого студента'})

        return data


class ReviewSerializers(serializers.Serializer):
    """Создание отзыва о компании (хранится в JSON)."""

    company_id = serializers.IntegerField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    text = serializers.CharField()

    def validate(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Отзыв только если студент подавал заявку в эту компанию.

        Args:
            data: company_id, rating, text.
        """
        request = self.context.get('request')
        from .permissions import get_user_student
        student = get_user_student(request.user) if request else None
        if not student:
            raise serializers.ValidationError('Отзыв могут оставлять только студенты')

        has_application = Application.objects.filter(
            student_id=student.id,
            vacancy__company_id=data['company_id'],
        ).exists()
        if not has_application:
            raise serializers.ValidationError(
                'Отзыв можно оставить только о компании, на вакансию которой вы подавали заявку.'
            )
        data['student_id'] = student.id
        return data
