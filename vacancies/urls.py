from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    VacancyViewSet, CompanyViewSet, StudentViewSet,
    ResumeViewSet, ApplicationViewSet
)

router = DefaultRouter()
router.register('vacancies', VacancyViewSet, basename='vacancy') #имя-ярлык для создания URL в коде
router.register('companies', CompanyViewSet, basename='company')
router.register('students', StudentViewSet, basename='student')
router.register('resumes', ResumeViewSet, basename='resume')
router.register('applications', ApplicationViewSet, basename='application')

urlpatterns = router.urls