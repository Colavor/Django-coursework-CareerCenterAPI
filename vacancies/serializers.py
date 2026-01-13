from rest_framework import serializers
from .models import Student, Company, Vacancy, Resume, Application


class VacancySerializers(serializers.ModelSerializer):
    company = serializers.PrimaryKeyRelatedField(queryset=Company.objects.all())

    class Meta:
        model = Vacancy
        fields = [
            'id', 'company', 'title', 'requirements', 'description',
            'salary', 'employment_type', 'schedule',
            'location', 'published_at', 'closed_at',
            'status', 'created_at', 'updated_at'
        ]

        read_only_fields = ['created_at', 'updated_at']

    def validate_salary(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError('Зарплата должна быть положительным числом')
        return value

    def validate(self, data):
        if 'published_at' in data:
            published = data['published_at']
        else:
            published = getattr(self.instance, 'published_at', None)  #оставляем старое

        if 'closed_at' in data:
            closed = data['closed_at']
        else:
            closed = getattr(self.instance, 'closed_at', None) #тоже самое оставляем старое, только дата закрытия

        if closed and published and closed < published:
            raise serializers.ValidationError({'closed_at': 'Дата закрытия не может быть раньше даты публикации'})
        return data


class StudentSerializers(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = [
            'id', 'first_name', 'last_name', 'email',
            'phone', 'birth_date', 'course', 'specialty',
            'group', 'faculty', 'photo'
        ]

    def validate_course(self, value):
        if value < 1 or value > 6:
            raise serializers.ValidationError('Курс должен быть в диапазоне от 1 до 6')
        return value


class CompanySerializers(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'description', 'website',
            'email', 'phone', 'industry', 'address',
            'logo', 'size'
        ]


class ResumeSerializers(serializers.ModelSerializer):
    student = serializers.PrimaryKeyRelatedField(queryset=Student.objects.all())

    class Meta:
        model = Resume
        fields = [
            'id', 'student', 'title', 'experience',
            'education', 'achievements', 'contacts',
            'status', 'skills_text', 'skills'
        ]


class ApplicationSerializers(serializers.ModelSerializer):
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

    def validate(self, data):
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
            # при редактировании чтобы текущая запись не считала сама себя дубликатом
            existing = existing.exclude(pk=self.instance.pk)
        if existing.exists():
            raise serializers.ValidationError(
                'Вы уже подавали заявку на эту вакансию.'
            )

        return data
