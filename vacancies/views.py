from django.utils import timezone
from django.db.models import Q, Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django.shortcuts import render, redirect

from .models import Student, Company, Vacancy, Resume, Application
from .serializers import (
    StudentSerializers,
    CompanySerializers,
    VacancySerializers,
    ResumeSerializers,
    ApplicationSerializers,
)

class VacancyViewSet(viewsets.ModelViewSet): #ModelViewSet — это готовый набор действий CRUD
    queryset = Vacancy.objects.all()  #Работай со всеми вакансиями в базе
    serializer_class = VacancySerializers #Когда нужно показать или принять вакансию в виде JSON, то мы используем сериализатор
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter] #Это список систем, которые мы добавляем к Api
    filterset_fields = ['company', 'employment_type', 'status', 'published_at', 'closed_at']
    search_fields = ['title', 'description', 'requirements']
    ordering_fields = ['salary', 'published_at', 'closed_at']
    ordering = ['-published_at']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user_id = self.request.query_params.get('user', None)
        if user_id:
            queryset = queryset.filter(created_by_id=user_id)
        created_by = self.request.query_params.get('created_by', None)
        if created_by:
            queryset = queryset.filter(created_by_id=created_by)
        return queryset

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

    #вакансии опубликованы в текущем году и активный статус или
    # или зарплата больше 10к и индустрия IT
    @action(detail=False, methods=['get'])
    def complex_vacancy(self, request, pk=None):
        current_year = timezone.now().year
        query = (
            Q(published_at__year=current_year, status='active') |
            Q(salary__gt=100000, company__industry__iexact='IT')
        )

        vacancies = Vacancy.objects.filter(query).distinct()
        serializer = self.get_serializer(vacancies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializers
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['industry', 'size']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'industry']
    ordering = ['name']

class StudentViewSet(viewsets.ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentSerializers
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


    #студенты 3-4 курс и имеют активное резюме
    #или подавали заявку в текущем месяце, но не на 1 курсе
    @action(detail=False, methods=['get'])
    def complex_filter(self, request):

        current_month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        query = (
            ((Q(course__in=[3, 4]) & Q(resumes__status='active')) |
            Q(applications__submitted_at__gte=current_month_start))
            & ~Q(course=1)
        )
        students = Student.objects.filter(query).distinct()
        serializer = self.get_serializer(students, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ResumeViewSet(viewsets.ModelViewSet):
    queryset = Resume.objects.all()
    serializer_class = ResumeSerializers
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['student', 'status']
    search_fields = ['title', 'experience', 'skills_text']
    ordering_fields = ['title', 'status']
    ordering = ['title']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_authenticated:
            user_filter = self.request.query_params.get('my', None)
            if user_filter:
                queryset = queryset.filter(created_by=self.request.user)
        return queryset

    @action(detail=True, methods=['post'])
    def resume_activate(self, request, pk=None):
        resume = self.get_object()
        resume.status = 'active'
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
    
    def get_queryset(self):
        queryset = super().get_queryset()
        student_id = self.request.query_params.get('student_id', None)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        return queryset

    @action(detail=False, methods=['get'])
    def my_applications(self, request):
        student_id = request.query_params.get('student')
        if not student_id:
            return Response(
                {'error': 'Необходимо указать параметр student'},
                status=status.HTTP_400_BAD_REQUEST
            )
        applications = Application.objects.filter(student_id=student_id)
        serializer = self.get_serializer(applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def withdraw(self, request, pk=None):
        application = self.get_object()
        application.status = 'withdraw'
        application.save()
        serializer = self.get_serializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)


def index(request):
    return render(request, 'vacancies/index.html')


def vacancy_list(request):
    vacancies = Vacancy.objects.all()[:20]
    return render(request, 'vacancies/vacancy_list.html', {'vacancies': vacancies})


def vacancy_add(request):
    if request.method == 'POST':
        try:
            company_id = request.POST.get('company')
            company = Company.objects.get(id=company_id)
            Vacancy.objects.create(
                title=request.POST.get('title'),
                company=company,
                description=request.POST.get('description'),
                requirements=request.POST.get('requirements', ''),
                salary=int(request.POST.get('salary')),
                status=request.POST.get('status', 'draft'),
                employment_type=request.POST.get('employment_type', 'full_time'),
                schedule=request.POST.get('schedule', ''),
                location=request.POST.get('location', '')
            )
            return redirect('/vacancies/')
        except Exception as e:
            companies = Company.objects.all()
            return render(request, 'vacancies/vacancy_form.html', {
                'companies': companies,
                'error': str(e)
            })
    companies = Company.objects.all()
    if not companies.exists():
        return render(request, 'vacancies/vacancy_form.html', {
            'companies': companies,
            'error': 'Нет компаний в базе данных. Сначала добавьте компанию через админку или API.'
        })
    return render(request, 'vacancies/vacancy_form.html', {'companies': companies})


def vacancy_edit(request, pk):
    vacancy = Vacancy.objects.get(id=pk)
    if request.method == 'POST':
        try:
            company_id = request.POST.get('company')
            company = Company.objects.get(id=company_id)
            vacancy.title = request.POST.get('title')
            vacancy.company = company
            vacancy.description = request.POST.get('description')
            vacancy.requirements = request.POST.get('requirements', '')
            vacancy.salary = int(request.POST.get('salary'))
            vacancy.status = request.POST.get('status', 'draft')
            vacancy.employment_type = request.POST.get('employment_type', 'full_time')
            vacancy.schedule = request.POST.get('schedule', '')
            vacancy.location = request.POST.get('location', '')
            vacancy.save()
            return redirect('/vacancies/')
        except Exception as e:
            companies = Company.objects.all()
            return render(request, 'vacancies/vacancy_form.html', {
                'vacancy': vacancy,
                'companies': companies,
                'error': str(e)
            })
    companies = Company.objects.all()
    return render(request, 'vacancies/vacancy_form.html', {'vacancy': vacancy, 'companies': companies})


def company_list(request):
    companies = Company.objects.all()[:20]
    return render(request, 'vacancies/company_list.html', {'companies': companies})


def company_add(request):
    if request.method == 'POST':
        try:
            company = Company.objects.create(
                name=request.POST.get('name'),
                email=request.POST.get('email'),
                industry=request.POST.get('industry'),
                description=request.POST.get('description', ''),
                phone=request.POST.get('phone', ''),
                address=request.POST.get('address', ''),
                website=request.POST.get('website', ''),
                size=request.POST.get('size', '')
            )
            if 'logo' in request.FILES:
                company.logo = request.FILES['logo']
                company.save()
            return redirect('/companies/')
        except Exception as e:
            return render(request, 'vacancies/company_form.html', {'error': str(e)})
    return render(request, 'vacancies/company_form.html')


def company_edit(request, pk):
    company = Company.objects.get(id=pk)
    if request.method == 'POST':
        try:
            company.name = request.POST.get('name')
            company.email = request.POST.get('email')
            company.industry = request.POST.get('industry')
            company.description = request.POST.get('description', '')
            company.phone = request.POST.get('phone', '')
            company.address = request.POST.get('address', '')
            company.website = request.POST.get('website', '')
            company.size = request.POST.get('size', '')
            if 'logo' in request.FILES:
                company.logo = request.FILES['logo']
            company.save()
            return redirect('/companies/')
        except Exception as e:
            return render(request, 'vacancies/company_form.html', {'company': company, 'error': str(e)})
    return render(request, 'vacancies/company_form.html', {'company': company})


def vacancy_delete(request, pk):
    vacancy = Vacancy.objects.get(id=pk)
    vacancy.delete()
    return redirect('/vacancies/')


def company_delete(request, pk):
    company = Company.objects.get(id=pk)
    company.delete()
    return redirect('/companies/')











