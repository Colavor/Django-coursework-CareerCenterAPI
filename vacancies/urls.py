from django.urls import path
from . import views

urlpatterns = [
    path('', views.vacancies, name='vacancies')
]
