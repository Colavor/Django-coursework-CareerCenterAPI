from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from vacancies.web_views import (
    index, login_view, register_view, logout_view,
    vacancy_list, vacancy_detail, vacancy_form, vacancy_delete,
    company_list, company_form, company_delete,
    favorites_list, favorite_add, favorite_remove,
    application_add, application_list, application_edit, application_quick_status,
    student_cabinet, student_form, student_list,
    user_list, user_toggle_active, user_toggle_staff,
    resume_form,
    review_list, review_add, review_moderate_list, review_moderate,
    analytics,
)

def trigger_error(request):
    division_by_zero = 1 / 0

urlpatterns = [
    path('', index, name='index'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),
    path('admin/', admin.site.urls),
    path('api/', include('vacancies.urls')),
    # студент
    path('vacancies/', vacancy_list, name='vacancy_list'),
    path('vacancies/<int:pk>/', vacancy_detail, name='vacancy_detail'),
    path('shortlist/', favorites_list, name='favorites_list'),
    path('shortlist/add/<int:pk>/', favorite_add, name='favorite_add'),
    path('shortlist/remove/<int:pk>/', favorite_remove, name='favorite_remove'),
    path('applications/add/<int:vacancy_id>/', application_add, name='application_add'),
    path('cabinet/', student_cabinet, name='student_cabinet'),
    path('students/<int:pk>/edit/', student_form, name='student_edit'),
    path('students/<int:student_id>/resume/add/', resume_form, name='resume_add'),
    path('resumes/<int:pk>/edit/', resume_form, name='resume_edit'),
    path('reviews/', review_list, name='review_list'),
    path('reviews/add/', review_add, name='review_add'),
    # администратор
    path('manage/vacancies/add/', vacancy_form, name='vacancy_add'),
    path('manage/vacancies/<int:pk>/edit/', vacancy_form, name='vacancy_edit'),
    path('manage/vacancies/<int:pk>/delete/', vacancy_delete, name='vacancy_delete'),
    path('manage/companies/', company_list, name='company_list'),
    path('manage/companies/add/', company_form, name='company_add'),
    path('manage/companies/<int:pk>/edit/', company_form, name='company_edit'),
    path('manage/companies/<int:pk>/delete/', company_delete, name='company_delete'),
    path('manage/applications/', application_list, name='application_list'),
    path('manage/applications/<int:pk>/', application_edit, name='application_edit'),
    path('manage/applications/<int:pk>/status/<str:status>/', application_quick_status, name='application_quick_status'),
    path('manage/students/', student_list, name='student_list'),
    path('manage/students/add/', student_form, name='student_add'),
    path('manage/users/', user_list, name='user_list'),
    path('manage/users/<int:pk>/toggle-active/', user_toggle_active, name='user_toggle_active'),
    path('manage/users/<int:pk>/toggle-staff/', user_toggle_staff, name='user_toggle_staff'),
    path('manage/reviews/', review_moderate_list, name='review_moderate_list'),
    path('manage/reviews/<int:review_id>/<str:action>/', review_moderate, name='review_moderate'),
    path('manage/analytics/', analytics, name='analytics'),
     path('sentry-debug/', trigger_error),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


if settings.DEBUG:
    urlpatterns += [
        path('silk/', include('silk.urls', namespace='silk')),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
