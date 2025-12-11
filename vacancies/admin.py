from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from simple_history.admin import SimpleHistoryAdmin

from .models import Vacancy, Student, Company, Resume, Application


class VacancyResource(resources.ModelResource):
    class Meta:
        model = Vacancy
        fields = ('id', 'title', 'company', 'salary', 'status', 'published_at')
        export_order = ('id', 'title', 'company', 'salary', 'status', 'published_at', 'applications_count')

    applications_count = resources.Field()  #количетсво заявок создаем поле, так как его нету в бд

    def get_export_queryset(self, request):
        queryset = super().get_export_queryset(request)
        return queryset.filter(status='active')

    def dehydrate_company(self, vacancy):
        return f"{vacancy.company.name} ({vacancy.company.industry})"

    def dehydrate_applications_count(self, vacancy):
        return vacancy.applications.count()


@admin.register(Vacancy)
class VacancyAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    resource_class = VacancyResource
    list_display = ['title', 'company', 'status', 'salary', 'published_at']
    list_filter = ['status', 'employment_type', 'company']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Application)
class ApplicationAdmin(ImportExportModelAdmin, SimpleHistoryAdmin):
    list_display = ['student', 'vacancy', 'status', 'submitted_at']
    list_filter = ['status', 'submitted_at']
    search_fields = ['student__first_name', 'student__last_name', 'vacancy__title']
    readonly_fields = ['submitted_at']


@admin.register(Student)
class StudentAdmin(SimpleHistoryAdmin):
    list_display = ['last_name', 'first_name', 'email', 'course', 'specialty']
    list_filter = ['course', 'faculty']
    search_fields = ['first_name', 'last_name', 'email']


@admin.register(Company)
class CompanyAdmin(SimpleHistoryAdmin):
    list_display = ['name', 'industry', 'email']
    list_filter = ['industry']
    search_fields = ['name', 'email']


@admin.register(Resume)
class ResumeAdmin(SimpleHistoryAdmin):
    list_display = ['student', 'title', 'status', 'created_at']
    list_filter = ['status']
    search_fields = ['student__first_name', 'student__last_name', 'title']
