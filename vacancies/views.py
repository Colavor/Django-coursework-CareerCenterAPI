from django.utils import timezone
from django.db.models import Q, Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Student, Company, Vacancy, Resume, Application
from .serializers import (
    StudentSerializers,
    CompanySerializers,
    VacancySerializers,
    ResumeSerializers,
    ApplicationSerializers,
)

class VacancyViewSet(viewsets.ModelViewSet): #ModelViewSet — это готовый набор действий: CRUD
    queryset = Vacancy.objects.all()  #«Работай со всеми вакансиями в базе».
    serializer_class = VacancySerializers #«Когда нужно показать или принять вакансию в виде JSON — используй этот сериализатор».
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter] #Это список систем, которые добавляют к твоему API:
    filterset_fields = ['company', 'employment_type', 'status', 'status', 'published_at', 'closed_at']
    search_fields = ['title', 'description', 'requirements']
    ordering_fields = ['salary', 'published_at', 'closed_at']
    ordering = ['-published_at']

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        vacancy = self.get_object()
        vacancy.status = 'closed'
        vacancy.closed_at = timezone.now()
        vacancy.save()
        serializer = self.get_serializer(vacancy)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def applications_count(self, request, pk=None):
        vacancy = self.get_object()
        count = vacancy.applications.count()
        return Response({'applications_count': count}, status=status.HTTP_200_OK)


    #Нужно дописать сложный Q запрос


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializers
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['industry', 'size']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'industry']
    ordering = ['name']

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializers
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['course', 'specialty', 'faculty']
    search_fields = ['first_name', 'last_name', 'email']
    ordering_fields = ['last_name', 'first_name', 'course']
    ordering = ['last_name', 'first_name']

    @action(detail=True, methods=['get'])
    def applications_statistics(self, request, pk=None):
        student = self.get_object()
        applications = student.applications.all()
        stats = {
            'total_sent': applications.count(),
            'invented': applications.filter(status='invented').count(),
            'rejected': applications.filter(status='rejected').count(),
            'accepted': applications.filter(status='accepted').count()
        }
        return Response(stats, status=status.HTTP_200_OK)


    #Здесь должен был быть сложный Q запрос


class ResumeViewSet(viewsets.ModelViewSet):
    queryset = Resume.objects.all()
    serializer_class = ResumeSerializers
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['student', 'status']
    search_fields = ['title', 'experience', 'skills']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']

    @action(detail=True, methods=['post'])
    def resume_activate(self, request, pk=None):
        resume = self.get_object()
        resume.status = 'activate'
        resume.save()
        serializer = self.get_serializer(resume)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializers
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['student', 'vacancy', 'status']
    search_fields = ['cover_letter']
    ordering_fields = ['submitted_at', 'status']
    ordering = ['-submitted_at']

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        application = self.get_object()
        application.status = 'withdraw'
        application.save()
        serializer = self.get_serializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)











