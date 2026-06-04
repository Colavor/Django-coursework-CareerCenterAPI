from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    VacancyViewSet, CompanyViewSet, StudentViewSet,
    ResumeViewSet, ApplicationViewSet,
    reviews_list, reviews_create, review_moderate,
)

router = DefaultRouter()
router.register('vacancies', VacancyViewSet, basename='vacancy')
router.register('companies', CompanyViewSet, basename='company')
router.register('students', StudentViewSet, basename='student')
router.register('resumes', ResumeViewSet, basename='resume')
router.register('applications', ApplicationViewSet, basename='application')

urlpatterns = router.urls + [
    path(
        'students/<int:student_id>/applications/',
        ApplicationViewSet.as_view({'get': 'list'}),
        name='student-applications'
    ),
    path('reviews/', reviews_list, name='reviews'),
    path('reviews/create/', reviews_create, name='reviews-create'),
    path('reviews/<int:review_id>/', review_moderate, name='review-moderate'),
]