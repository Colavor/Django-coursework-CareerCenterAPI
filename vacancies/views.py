"""
REST API центра карьеры: вакансии, заявки, shortlist, отзывы.

ViewSet'ы и вспомогательные функции для аннотаций и JSON-хранилища отзывов.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db.models import Q, Count, Case, When, Value, IntegerField, FloatField, QuerySet
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from .models import Student, Company, Vacancy, Resume, Application
from .permissions import (
    IsAdmin, IsStudent, IsAdminOrReadOnly,
    IsAdminOrApplicationOwner, IsAdminOrStudentOwner,
    get_user_student,
)
from .serializers import (
    StudentSerializers,
    CompanySerializers,
    VacancySerializers,
    ResumeSerializers,
    ApplicationSerializers,
    ReviewSerializers,
)

REVIEWS_FILE = Path(settings.BASE_DIR) / 'reviews.json'
SHORTLIST_STATS_FILE = Path(settings.BASE_DIR) / 'shortlist_stats.json'


def load_reviews() -> list[dict[str, Any]]:
    """
    Загрузить список отзывов из reviews.json.

    Returns:
        Список словарей отзывов или пустой список, если файла нет.
    """
    if REVIEWS_FILE.exists():
        with open(REVIEWS_FILE, encoding='utf-8') as f:
            return json.load(f)
    return []


def save_reviews(reviews: list[dict[str, Any]]) -> None:
    """
    Сохранить список отзывов в reviews.json.

    Args:
        reviews: Полный список отзывов для записи в файл.
    """
    with open(REVIEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(reviews, f, ensure_ascii=False, indent=2)


def load_shortlist_stats() -> dict[str, int]:
    """
    Загрузить счётчики добавлений в shortlist по вакансиям.

    Returns:
        Словарь {vacancy_id: count} или пустой словарь.
    """
    if SHORTLIST_STATS_FILE.exists():
        with open(SHORTLIST_STATS_FILE, encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_shortlist_stats(stats: dict[str, int]) -> None:
    """
    Сохранить счётчики shortlist в JSON.

    Args:
        stats: Словарь {vacancy_id: count}.
    """
    with open(SHORTLIST_STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def add_shortlist_stat(vacancy_id: int) -> None:
    """
    Увеличить счётчик shortlist для вакансии.

    Args:
        vacancy_id: Id вакансии в shortlist_stats.json.
    """
    stats = load_shortlist_stats()
    key = str(vacancy_id)
    stats[key] = stats.get(key, 0) + 1
    save_shortlist_stats(stats)


def remove_shortlist_stat(vacancy_id: int) -> None:
    """
    Уменьшить счётчик shortlist для вакансии.

    Args:
        vacancy_id: Id вакансии в shortlist_stats.json.
    """
    stats = load_shortlist_stats()
    key = str(vacancy_id)
    if stats.get(key, 0) > 0:
        stats[key] -= 1
    save_shortlist_stats(stats)


def get_company_avg_ratings() -> dict[int, float]:
    """
    Средний рейтинг по одобренным отзывам для каждой компании.

    Returns:
        Словарь {company_id: средний rating}.
    """
    ratings = {}
    counts = {}
    for review in load_reviews():
        if not review.get('is_approved'):
            continue
        cid = review.get('company_id')
        if cid is None:
            continue
        ratings[cid] = ratings.get(cid, 0) + review.get('rating', 0)
        counts[cid] = counts.get(cid, 0) + 1
    return {cid: round(ratings[cid] / counts[cid], 1) for cid in ratings}


def annotate_vacancies(queryset: QuerySet[Vacancy]) -> QuerySet[Vacancy]:
    """
    Аннотации: число заявок, shortlist, средний рейтинг компании.

    Args:
        queryset: QuerySet вакансий.

    Returns:
        QuerySet с полями applications_count, shortlist_count, company_avg_rating.
    """
    queryset = queryset.annotate(applications_count=Count('applications'))

    stats = load_shortlist_stats()
    if stats:
        shortlist_whens = [
            When(pk=int(vid), then=Value(cnt))
            for vid, cnt in stats.items()
        ]
        queryset = queryset.annotate(
            shortlist_count=Case(*shortlist_whens, default=Value(0), output_field=IntegerField())
        )
    else:
        queryset = queryset.annotate(
            shortlist_count=Value(0, output_field=IntegerField())
        )

    company_ratings = get_company_avg_ratings()
    if company_ratings:
        rating_whens = [
            When(company_id=int(cid), then=Value(avg))
            for cid, avg in company_ratings.items()
        ]
        queryset = queryset.annotate(
            company_avg_rating=Case(*rating_whens, default=Value(0.0), output_field=FloatField())
        )
    else:
        queryset = queryset.annotate(
            company_avg_rating=Value(0.0, output_field=FloatField())
        )

    return queryset


def get_shortlist(request: Request) -> tuple[list[int] | None, str | None]:
    """
    Id вакансий в shortlist студента из сессии.

    Args:
        request: HTTP-запрос API.

    Returns:
        Кортеж (список id вакансий, None) или (None, текст ошибки).
    """
    student = get_user_student(request.user)
    if not student:
        return None, 'Доступ только для студента'
    key = f'shortlist_{student.id}'
    return request.session.get(key, []), None


class VacancyViewSet(viewsets.ModelViewSet):
    """API вакансий: CRUD, фильтры, shortlist, аннотации."""

    serializer_class = VacancySerializers
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['company', 'employment_type', 'status', 'published_at', 'closed_at']
    search_fields = ['title', 'description', 'requirements']
    ordering_fields = ['salary', 'published_at', 'closed_at']
    ordering = ['-published_at']

    def get_queryset(self) -> QuerySet[Vacancy]:
        """
        Вакансии с компанией, аннотациями и опциональным фильтром автора.

        Returns:
            QuerySet с select_related, annotate и query-параметрами user/created_by.
        """
        queryset = annotate_vacancies(
            Vacancy.objects.select_related('company').all()
        )
        user_id = self.request.query_params.get('user', None)
        if user_id:
            queryset = queryset.filter(created_by_id=user_id)
        created_by = self.request.query_params.get('created_by', None)
        if created_by:
            queryset = queryset.filter(created_by_id=created_by)
        return queryset

    def get_serializer_context(self) -> dict[str, Any]:
        """
        Передать favorite_vacancies в сериализатор для поля is_favorite.

        Returns:
            Контекст сериализатора с id вакансий из shortlist студента.
        """
        context = super().get_serializer_context()
        student = get_user_student(self.request.user)
        if student:
            key = f'shortlist_{student.id}'
            context['favorite_vacancies'] = self.request.session.get(key, [])
        else:
            context['favorite_vacancies'] = []
        return context

    # --- студент: shortlist ---
    @action(detail=True, methods=['post'], permission_classes=[IsStudent])
    def add_to_shortlist(self, request: Request, pk: int | None = None) -> Response:
        """
        Добавить активную вакансию в shortlist студента.

        Args:
            request: HTTP-запрос студента.
            pk: Id вакансии.

        Returns:
            Response со списком id в shortlist или 400, если вакансия не active.
        """
        vacancy = self.get_object()
        if vacancy.status != 'active':
            return Response(
                {'error': 'Вакансия недоступна (не активна).'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        student = get_user_student(request.user)
        key = f'shortlist_{student.id}'
        shortlist = request.session.get(key, [])
        vid = int(pk)
        if vid not in shortlist:
            shortlist.append(vid)
            add_shortlist_stat(vid)
        request.session[key] = shortlist
        return Response({'shortlist': shortlist})

    @action(detail=False, methods=['get'], permission_classes=[IsStudent])
    def my_shortlist(self, request: Request) -> Response:
        """
        Список вакансий из shortlist текущего студента.

        Args:
            request: HTTP-запрос студента.

        Returns:
            Response с сериализованными вакансиями из сессии.
        """
        shortlist, err = get_shortlist(request)
        if err:
            return Response({'error': err}, status=status.HTTP_400_BAD_REQUEST)
        vacancies = annotate_vacancies(
            Vacancy.objects.filter(id__in=shortlist).select_related('company')
        )
        serializer = self.get_serializer(
            vacancies, many=True,
            context={'favorite_vacancies': shortlist, 'request': request},
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsStudent])
    def remove_from_shortlist(
        self, request: Request, pk: int | None = None,
    ) -> Response:
        """
        Удалить вакансию из shortlist текущего студента.

        Args:
            request: HTTP-запрос студента.
            pk: Id вакансии.

        Returns:
            Response с обновлённым списком id в shortlist.
        """
        student = get_user_student(request.user)
        key = f'shortlist_{student.id}'
        shortlist = request.session.get(key, [])
        vid = int(pk)
        if vid in shortlist:
            shortlist.remove(vid)
            remove_shortlist_stat(vid)
        request.session[key] = shortlist
        return Response({'shortlist': shortlist})

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def close(self, request: Request, pk: int | None = None) -> Response:
        """
        Закрыть вакансию и установить дату закрытия.

        Доступно только администратору. Статус → closed, closed_at → сейчас.

        Args:
            request: HTTP-запрос администратора.
            pk: Id вакансии.

        Returns:
            Response с данными закрытой вакансии.
        """
        vacancy = self.get_object()
        vacancy.status = 'closed'
        vacancy.closed_at = timezone.now()
        vacancy.save()
        serializer = self.get_serializer(vacancy)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'])
    def applications_count(
        self, request: Request, pk: int | None = None,
    ) -> Response:
        """
        Количество заявок на вакансию.

        Args:
            request: HTTP-запрос.
            pk: Id вакансии.

        Returns:
            Response с полем applications_count.
        """
        vacancy = self.get_object()
        count = vacancy.applications.count()
        return Response({'applications_count': count}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def complex_vacancy(self, request: Request, pk: int | None = None) -> Response:
        """
        Сложный фильтр вакансий (Q): активные за текущий год или IT с зарплатой > 100k.

        Args:
            request: HTTP-запрос.

        Returns:
            Response со списком подходящих вакансий с аннотациями.
        """
        current_year = timezone.now().year
        query = (
            Q(published_at__year=current_year, status='active') |
            Q(salary__gt=100000, company__industry__iexact='IT')
        )

        vacancies = annotate_vacancies(
            Vacancy.objects.filter(query).select_related('company').distinct()
        )
        serializer = self.get_serializer(vacancies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CompanyViewSet(viewsets.ModelViewSet):
    """API компаний-работодателей: CRUD для админа, чтение для всех."""

    queryset = Company.objects.all()
    serializer_class = CompanySerializers
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['industry', 'size']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'industry']
    ordering = ['name']


class StudentViewSet(viewsets.ModelViewSet):
    """API студентов: CRUD для админа, профиль и статистика через actions."""

    queryset = Student.objects.all()
    serializer_class = StudentSerializers
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['course', 'specialty', 'faculty']
    search_fields = ['first_name', 'last_name', 'email']
    ordering_fields = ['last_name', 'first_name', 'course']
    ordering = ['last_name', 'first_name']

    @action(detail=True, methods=['get'])
    def applications_statistics(
        self, request: Request, pk: int | None = None,
    ) -> Response:
        """
        Статистика заявок студента по статусам.

        Args:
            request: HTTP-запрос.
            pk: Id студента.

        Returns:
            Response: total_sent, invited, rejected, accepted.
        """
        student = self.get_object()
        applications = student.applications.all()
        stats = {
            'total_sent': applications.count(),
            'invited': applications.filter(status='invited').count(),
            'rejected': applications.filter(status='rejected').count(),
            'accepted': applications.filter(status='accepted').count()
        }
        return Response(stats, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def complex_filter(self, request: Request) -> Response:
        """
        Сложный фильтр студентов (Q): 3–4 курс с резюме или заявка в этом месяце, не 1 курс.

        Args:
            request: HTTP-запрос.

        Returns:
            Response со списком подходящих студентов.
        """
        current_month_start = timezone.now().replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        query = (
            (
                (Q(course__in=[3, 4]) & Q(resumes__status='active'))
                | Q(applications__submitted_at__gte=current_month_start)
            )
            & ~Q(course=1)
        )
        students = Student.objects.filter(query).distinct()
        serializer = self.get_serializer(students, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticated, IsAdminOrStudentOwner])
    def my_profile(self, request: Request, pk: int | None = None) -> Response:
        """
        Просмотр профиля студента (свой или любой — для админа).

        Args:
            request: HTTP-запрос.
            pk: Id студента.

        Returns:
            Response с данными профиля.
        """
        student = self.get_object()
        serializer = self.get_serializer(student)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'], permission_classes=[IsAuthenticated, IsAdminOrStudentOwner])
    def update_profile(self, request: Request, pk: int | None = None) -> Response:
        """
        Частичное обновление профиля студента.

        Args:
            request: HTTP-запрос с полями для PATCH.
            pk: Id студента.

        Returns:
            Response с обновлённым профилем.
        """
        student = self.get_object()
        serializer = self.get_serializer(student, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ResumeViewSet(viewsets.ModelViewSet):
    """API резюме студентов."""

    serializer_class = ResumeSerializers
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['student', 'status']
    search_fields = ['title', 'experience', 'skills_text']
    ordering_fields = ['title', 'status']
    ordering = ['title']

    def get_queryset(self) -> QuerySet[Resume]:
        """Резюме с данными студента (select_related)."""
        return Resume.objects.select_related('student')

    @action(detail=True, methods=['post'])
    def resume_activate(self, request: Request, pk: int | None = None) -> Response:
        """
        Перевести резюме в статус active.

        Args:
            request: HTTP-запрос.
            pk: Id резюме.

        Returns:
            Response с обновлённым резюме.
        """
        resume = self.get_object()
        resume.status = 'active'
        resume.save()
        serializer = self.get_serializer(resume)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ApplicationViewSet(viewsets.ModelViewSet):
    """API заявок: создание студентом, просмотр с проверкой прав, статусы."""

    serializer_class = ApplicationSerializers
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['student', 'vacancy', 'status']
    search_fields = ['cover_letter']
    ordering_fields = ['submitted_at', 'status']
    ordering = ['-submitted_at']

    def get_permissions(self) -> list[Any]:
        """
        Права по action: админ — список и статусы; студент — создание; retrieve — владелец или админ.

        Returns:
            Список экземпляров permission-классов для текущего action.
        """
        if self.action in ['list', 'change_status', 'analytics', 'update', 'partial_update', 'destroy']:
            return [IsAdmin()]
        if self.action in ['create', 'my_applications', 'withdraw']:
            return [IsStudent()]
        if self.action == 'retrieve':
            return [IsAuthenticated(), IsAdminOrApplicationOwner()]
        return [IsAuthenticated()]

    def retrieve(self, request: Request, *args: Any, **kwargs: Any) -> Response:
        """
        Детали заявки с проверкой IsAdminOrApplicationOwner.

        Returns:
            Response с заявкой или 403, если не админ и не автор.
        """
        application = self.get_object()
        self.check_object_permissions(request, application)
        serializer = self.get_serializer(application)
        return Response(serializer.data)

    def get_queryset(self) -> QuerySet[Application]:
        """
        Заявки с select_related; для retrieve — ещё вакансия и резюме.

        Returns:
            QuerySet с опциональным фильтром student_id из query-параметра.
        """
        if self.action == 'retrieve':
            queryset = Application.objects.select_related('vacancy', 'resume', 'student')
        else:
            queryset = Application.objects.select_related('student')

        student_id = self.request.query_params.get('student_id', None)
        if student_id:
            queryset = queryset.filter(student_id=student_id)
        return queryset

    @action(detail=False, methods=['get'])
    def my_applications(self, request: Request) -> Response:
        """
        Список заявок текущего студента.

        Args:
            request: HTTP-запрос студента.

        Returns:
            Response со всеми заявками студента.
        """
        student = get_user_student(request.user)
        applications = Application.objects.filter(student=student).select_related(
            'student', 'vacancy', 'resume'
        )
        serializer = self.get_serializer(applications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # --- администратор: смена статуса заявки ---
    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def change_status(self, request: Request, pk: int | None = None) -> Response:
        """
        Смена статуса заявки администратором.

        Args:
            request: HTTP-запрос с полем status.
            pk: Id заявки.

        Returns:
            Response с обновлённой заявкой или 400 при неверном статусе.
        """
        application = self.get_object()
        new_status = request.data.get('status')
        allowed = [s[0] for s in Application.STATUS_CHOICES]
        if new_status not in allowed:
            return Response({'error': 'Неверный статус'}, status=status.HTTP_400_BAD_REQUEST)
        application.status = new_status
        application.save()
        serializer = self.get_serializer(application)
        return Response(serializer.data)

    # --- администратор: аналитика ---
    @action(detail=False, methods=['get'], permission_classes=[IsAdmin])
    def analytics(self, request: Request) -> Response:
        """
        Сводная аналитика для администратора.

        Args:
            request: HTTP-запрос администратора.

        Returns:
            Response: число вакансий, активных вакансий, заявок и студентов.
        """
        stats = {
            'vacancies_total': Vacancy.objects.count(),
            'vacancies_active': Vacancy.objects.filter(status='active').count(),
            'applications_total': Application.objects.count(),
            'students_total': Student.objects.count(),
        }
        return Response(stats)

    @action(detail=True, methods=['post'])
    def withdraw(self, request: Request, pk: int | None = None) -> Response:
        """
        Отозвать свою заявку (статус withdrawn).

        Args:
            request: HTTP-запрос студента-автора.
            pk: Id заявки.

        Returns:
            Response с заявкой или 403, если не автор.
        """
        application = self.get_object()
        student = get_user_student(request.user)
        if application.student_id != student.id:
            return Response({'error': 'Нет доступа'}, status=status.HTTP_403_FORBIDDEN)
        application.status = 'withdrawn'
        application.save()
        serializer = self.get_serializer(application)
        return Response(serializer.data, status=status.HTTP_200_OK)


# --- отзывы ---
@api_view(['GET'])
@permission_classes([AllowAny])
def reviews_list(request: Request) -> Response:
    """
    Список отзывов; гостям и студентам — только одобренные.

    Args:
        request: HTTP-запрос.

    Returns:
        Response со списком отзывов из reviews.json.
    """
    reviews = load_reviews()
    if not request.user.is_authenticated or not request.user.is_staff:
        reviews = [r for r in reviews if r.get('is_approved')]
    return Response(reviews)


@api_view(['POST'])
@permission_classes([IsStudent])
def reviews_create(request: Request) -> Response:
    """
    Создать отзыв студентом (на модерации, is_approved=False).

    Args:
        request: HTTP-запрос с company_id, rating, text.

    Returns:
        Response с новым отзывом, статус 201.
    """
    serializer = ReviewSerializers(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)
    reviews = load_reviews()
    new_id = max([r.get('id', 0) for r in reviews], default=0) + 1
    review = serializer.validated_data.copy()
    review['id'] = new_id
    review['is_approved'] = False
    reviews.append(review)
    save_reviews(reviews)
    return Response(review, status=status.HTTP_201_CREATED)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsAdmin])
def review_moderate(request: Request, review_id: int) -> Response:
    """
    Модерация отзыва: PATCH (одобрение/правка) или DELETE.

    Args:
        request: HTTP-запрос администратора.
        review_id: Id отзыва в reviews.json.

    Returns:
        Response с отзывом, 204 при DELETE или 404, если не найден.
    """
    reviews = load_reviews()
    review = None
    for r in reviews:
        if r.get('id') == review_id:
            review = r
            break
    if not review:
        return Response({'error': 'Отзыв не найден'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'DELETE':
        reviews.remove(review)
        save_reviews(reviews)
        return Response(status=status.HTTP_204_NO_CONTENT)

    review['is_approved'] = request.data.get('is_approved', True)
    if 'text' in request.data:
        review['text'] = request.data['text']
    if 'rating' in request.data:
        review['rating'] = request.data['rating']
    save_reviews(reviews)
    return Response(review)

