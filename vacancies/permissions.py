from __future__ import annotations

from typing import Any

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.request import Request
from rest_framework.views import APIView

from .models import Student


def get_user_student(user: AbstractBaseUser | AnonymousUser) -> Student | None:
    """
    Профиль студента по email текущего пользователя.

    Args:
        user: Пользователь Django (сессия/API).

    Returns:
        Student или None для гостя/администратора.
    """
    if not user.is_authenticated or user.is_staff:
        return None
    return Student.objects.filter(email=user.email).first()


class IsAdmin(BasePermission):
    """Доступ только администратору (is_staff)."""

    message = 'Доступ только для администратора'

    def has_permission(self, request: Request, view: APIView) -> bool:
        return request.user.is_authenticated and request.user.is_staff


class IsStudent(BasePermission):
    """Доступ только студенту"""

    message = 'Доступ только для студента'

    def has_permission(self, request: Request, view: APIView) -> bool:
        return request.user.is_authenticated and not request.user.is_staff


class IsAdminOrReadOnly(BasePermission):
    """Чтение всем; изменение только администратору."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.is_staff


class IsAdminOrApplicationOwner(BasePermission):
    """Заявку видит админ или студент-автор."""

    message = 'Нет доступа к этой заявке'

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if request.user.is_staff:
            return True
        student = get_user_student(request.user)
        return student is not None and obj.student_id == student.id


class IsAdminOrStudentOwner(BasePermission):
    """Профиль студента редактирует админ или сам студент."""

    message = 'Нет доступа к профилю'

    def has_object_permission(self, request: Request, view: APIView, obj: Any) -> bool:
        if request.user.is_staff:
            return True
        student = get_user_student(request.user)
        return student is not None and obj.id == student.id
