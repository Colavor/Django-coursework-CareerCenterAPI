from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from import_export.formats import base_formats
from simple_history.admin import SimpleHistoryAdmin

from .models import Vacancy, Student, Company, Resume, Application, Skill


class VacancyResource(resources.ModelResource):
    class Meta:
        model = Vacancy
        fields = ('id', 'title', 'company', 'salary', 'status', 'published_at', 'applications_count')
        export_order = ('id', 'title', 'company', 'salary', 'status', 'published_at', 'applications_count')

    applications_count = resources.Field()  #количетсво заявок создаем поле, так как его нету в бд

    def get_export_queryset(self, request):
        queryset = super().get_export_queryset(request)
        return queryset.filter(status='active')

    def dehydrate_company(self, vacancy):
        return f"{vacancy.company.name} ({vacancy.company.industry})"

    def dehydrate_applications_count(self, vacancy):
        return vacancy.applications.count()


class ApplicationInline(admin.TabularInline):
    model = Application
    extra = 0
    raw_id_fields = ['student', 'vacancy', 'resume']
    readonly_fields = ['submitted_at']


@admin.register(Vacancy)
class VacancyAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    resource_class = VacancyResource
    formats = [base_formats.XLSX, base_formats.CSV]
    list_display = ['title', 'company', 'status', 'salary', 'published_at', 'get_applications_count']
    list_display_links = ['title', 'company']
    list_filter = ['status', 'employment_type', 'company', 'published_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'published_at'
    raw_id_fields = ['company', 'created_by', 'updated_by']
    filter_horizontal = []

    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'company', 'description', 'requirements')
        }),
        ('Условия работы', {
            'fields': ('salary', 'employment_type', 'schedule', 'location')
        }),
        ('Статус и даты', {
            'fields': ('status', 'published_at', 'closed_at')
        }),
        ('Системная информация', {
            'fields': ('created_by', 'updated_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [ApplicationInline]

    @admin.display(description='Количество заявок')
    def get_applications_count(self, obj):
        return obj.applications.count()
    get_applications_count.short_description = 'Заявок'


@admin.register(Application)
class ApplicationAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    formats = [base_formats.XLSX, base_formats.CSV]
    list_display = ['student', 'vacancy', 'status', 'submitted_at', 'get_days_since_submit']
    list_display_links = ['student', 'vacancy']
    list_filter = ['status', 'submitted_at']
    search_fields = ['student__first_name', 'student__last_name', 'vacancy__title']
    readonly_fields = ['submitted_at']
    date_hierarchy = 'submitted_at'
    raw_id_fields = ['student', 'vacancy', 'resume']

    fieldsets = (
        ('Основная информация', {
            'fields': ('student', 'vacancy', 'resume', 'status')
        }),
        ('Детали заявки', {
            'fields': ('cover_letter', 'employer_comment', 'response_date')
        }),
        ('Системная информация', {
            'fields': ('submitted_at',),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Дней с подачи')
    def get_days_since_submit(self, obj):
        if obj.submitted_at:
            from django.utils import timezone
            delta = timezone.now() - obj.submitted_at
            return delta.days
        return '-'


class ResumeInline(admin.TabularInline):
    model = Resume
    extra = 0
    raw_id_fields = ['student']


@admin.register(Student)
class StudentAdmin(SimpleHistoryAdmin):
    list_display = ['last_name', 'first_name', 'email', 'course', 'specialty', 'get_resumes_count']
    list_display_links = ['last_name', 'first_name']
    list_filter = ['course', 'faculty']
    search_fields = ['first_name', 'last_name', 'email']

    fieldsets = (
        ('Личные данные', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'birth_date', 'photo')
        }),
        ('Учебная информация', {
            'fields': ('course', 'specialty', 'group', 'faculty')
        }),
    )

    inlines = [ResumeInline]

    @admin.display(description='Резюме')
    def get_resumes_count(self, obj):
        return obj.resumes.count()


class VacancyInline(admin.TabularInline):
    model = Vacancy
    extra = 0
    raw_id_fields = ['company']


@admin.register(Company)
class CompanyAdmin(SimpleHistoryAdmin):
    list_display = ['name', 'industry', 'email', 'get_vacancies_count']
    list_display_links = ['name', 'industry']
    list_filter = ['industry', 'size']
    search_fields = ['name', 'email', 'industry']

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'description', 'logo', 'industry', 'size')
        }),
        ('Контакты', {
            'fields': ('email', 'phone', 'website', 'address')
        }),
    )

    inlines = [VacancyInline]

    @admin.display(description='Вакансий')
    def get_vacancies_count(self, obj):
        return obj.vacancies.count()


@admin.register(Resume)
class ResumeAdmin(SimpleHistoryAdmin):
    list_display = ['student', 'title', 'status', 'get_skills_count']
    list_display_links = ['student', 'title']
    list_filter = ['status']
    search_fields = ['student__first_name', 'student__last_name', 'title']
    raw_id_fields = ['student', 'created_by', 'updated_by']
    filter_horizontal = ['skills']

    fieldsets = (
        ('Основная информация', {
            'fields': ('student', 'title', 'status')
        }),
        ('Содержание', {
            'fields': ('experience', 'education', 'achievements', 'contacts', 'skills_text')
        }),
        ('Навыки', {
            'fields': ('skills',)
        }),
        ('Системная информация', {
            'fields': ('created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Навыков')
    def get_skills_count(self, obj):
        return obj.skills.count()


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_description_preview']
    list_display_links = ['name']
    search_fields = ['name', 'description']

    @admin.display(description='Описание')
    def get_description_preview(self, obj):
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return '-'
