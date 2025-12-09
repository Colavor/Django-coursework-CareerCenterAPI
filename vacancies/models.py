from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords

class Vacancy(models.Model):
    EMPLOYMENT_CHOICES = [
        ('full_time', 'Полная занятость'),
        ('part_time', 'Частичная занятость'),
        ('internship', 'Стажировка'),
        ('contract', 'Контракт'),
        ('remote', 'Удалённо'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('active', 'Активна'),
        ('closed', 'Закрыта'),
        ('archived', 'Архив'),
    ]

    company = models.ForeignKey('Company', verbose_name='Компания',on_delete=models.CASCADE,related_name='vacancies')
    title = models.CharField('Название вакансии', max_length=100)
    requirements = models.TextField('Требования', blank=True)
    description = models.TextField('Описание')
    salary = models.PositiveIntegerField('Зарплата', default=1)
    employment_type = models.CharField('Тип занятости', max_length=50, choices=EMPLOYMENT_CHOICES ,default='full_time')
    schedule = models.CharField('График работы', max_length=100, blank=True)
    published_at = models.DateTimeField('Дата публикации', default=timezone.now)
    closed_at = models.DateTimeField('Дата закрытия', null=True, blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='draft')
    location = models.CharField('Локация', max_length=150, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Вакансия'
        verbose_name_plural = 'Вакансии'
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['published_at']),
            models.Index(fields=['salary']),
            models.Index(fields=['company']),
        ]

    def clean(self):
        super().clean()
        if self.salary is None or self.salary <= 0:
            raise ValidationError({'salary': 'Зарплата должна быть положительным числом'})
        if self.closed_at and self.closed_at < self.published_at:
            raise ValidationError({'closed_at': 'Дата закрытия не может быть раньше даты публикации.'})
        if self.published_at and self.published_at > timezone.now():
            raise ValidationError({'published_at': 'Дата публикации не может быть в будущем.'})

    def __str__(self):
        return f'{self.title} - {self.company}'



class Student(models.Model):
    first_name = models.CharField('Имя', max_length=30)
    last_name = models.CharField('Фамилия', max_length=30)
    email = models.EmailField('Email', unique=True)
    phone = models.CharField('Номер телефона', max_length=20, blank=True)
    birth_date = models.DateField('Дата рождения')
    course = models.PositiveSmallIntegerField('Курс обучения', default=1)
    specialty = models.CharField('Специальность', max_length=150)
    group = models.CharField('Группа', max_length=50, blank=True)
    faculty = models.CharField('Факультет', max_length=150, blank=True)
    photo = models.ImageField('Фото', upload_to='students/photos/', null=True, blank=True)

    history = HistoricalRecords()

    def clean(self):
        super().clean()
        if self.course is not None and (self.course < 1 or self.course > 6):
            raise ValidationError({'course': 'Курс должен быть в диапазоне от 1 до 6'})
        if self.birth_date and self.birth_date > timezone.now().date():
            raise ValidationError({'birth_date': 'Дата рождения не может быть в будущем.'})

    class Meta:
        verbose_name = 'Студент'
        verbose_name_plural = 'Студенты'
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f'{self.last_name} {self.first_name} ({self.email})'


class Company(models.Model):
    name = models.CharField('Название', max_length=255)
    description = models.TextField('Описание', blank=True)
    website = models.URLField('Сайт', blank=True)
    email = models.EmailField('Email')
    phone = models.CharField('Телефон', max_length=50, blank=True)
    industry = models.CharField('Отрасль', max_length=100)
    address = models.CharField('Адрес', max_length=255, blank=True)
    logo = models.ImageField('Логотип', upload_to='companies/logos/', null=True, blank=True)
    size = models.CharField('Размер компании', max_length=50, blank=True)

    history = HistoricalRecords()

    def __str__(self):
        return f'{self.name} ({self.email})'

    class Meta:
        verbose_name = 'Компания'
        verbose_name_plural = 'Компании'
        ordering = ['industry']
        indexes = [
            models.Index(fields=['industry']),
        ]

class Resume(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('active', 'Активно'),
        ('archived', 'Архив')
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='resumes')
    title = models.CharField('Название резюме', max_length=200, default='Основное резюме')
    experience = models.TextField('Опыт работы')
    education = models.TextField('Образование', blank=True)
    achievements = models.TextField('Достижения', blank=True)
    contacts = models.TextField('Контакты')
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='draft')
    skills = models.TextField('Навыки', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Резюме'
        verbose_name_plural = 'Резюме'
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.student} — {self.title}"


class Application(models.Model):
    STATUS_CHOICES = [
        ('sent', 'Отправлена'),
        ('viewed', 'Просмотрена'),
        ('invited', 'Приглашение'),
        ('rejected', 'Отказ'),
        ('accepted', 'Принята'),
        ('withdrawn', 'Отозвана'),
    ]

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='applications')
    vacancy = models.ForeignKey(Vacancy, on_delete=models.CASCADE, related_name='applications')
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='applications')
    cover_letter = models.TextField('Сопроводительное письмо', blank=True)
    submitted_at = models.DateTimeField('Дата подачи', auto_now_add=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='sent')
    response_date = models.DateTimeField('Дата ответа', null=True, blank=True)
    employer_comment = models.TextField('Комментарий работодателя')

    history = HistoricalRecords()

    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        unique_together = ('student', 'vacancy') #один студент может откликнуться только на одну ваканисю
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['submitted_at']),
        ]

    def clean(self):
        if self.resume and self.resume.student_id != self.student_id:
            raise ValidationError({'resume': 'Выбранное резюме не принадлежит этому студенту.'})
        if not self.resume:
            raise ValidationError({'resume': 'Для подачи заявки требуется указать резюме.'})
        if self.resume and getattr(self.resume, 'status', None) != 'active':
            raise ValidationError(
                {'resume': 'Для подачи заявки требуется активное резюме.'})

    def __str__(self):
        return f'{self.student} - {self.vacancy}'
