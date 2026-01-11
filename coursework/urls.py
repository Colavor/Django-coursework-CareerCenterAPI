from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from vacancies.views import (
    index, vacancy_list, vacancy_add, vacancy_edit, vacancy_delete,
    company_list, company_add, company_edit, company_delete
)


urlpatterns = [
    path('', index, name='index'),
    path('admin/', admin.site.urls),
    path('api/', include('vacancies.urls')),
    path('vacancies/', vacancy_list, name='vacancy_list'),
    path('vacancies/add/', vacancy_add, name='vacancy_add'),
    path('vacancies/<int:pk>/edit/', vacancy_edit, name='vacancy_edit'),
    path('vacancies/<int:pk>/delete/', vacancy_delete, name='vacancy_delete'),
    path('companies/', company_list, name='company_list'),
    path('companies/add/', company_add, name='company_add'),
    path('companies/<int:pk>/edit/', company_edit, name='company_edit'),
    path('companies/<int:pk>/delete/', company_delete, name='company_delete'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)