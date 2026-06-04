from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.db.models import Count
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ValidationError

from .models import Student, Company, Vacancy, Resume, Application
from .views import load_reviews, save_reviews, add_shortlist_stat, remove_shortlist_stat, annotate_vacancies


def is_admin(user):
    return user.is_authenticated and user.is_staff


def admin_required(view):
    return login_required(user_passes_test(is_admin)(view))


def get_current_student(request):
    if not request.user.is_authenticated or request.user.is_staff:
        return None
    return Student.objects.filter(email=request.user.email).first()


def student_required(view):
    @login_required
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_staff:
            return redirect('index')
        student = get_current_student(request)
        if not student:
            return redirect('register')
        return view(request, student=student, *args, **kwargs)
    return wrapper


def get_shortlist_ids(request, student):
    return request.session.get(f'shortlist_{student.id}', [])


def enrich_reviews(reviews):
    if not reviews:
        return []
    company_ids = {r.get('company_id') for r in reviews if r.get('company_id') is not None}
    names = dict(Company.objects.filter(id__in=company_ids).values_list('id', 'name'))
    result = []
    for r in reviews:
        item = dict(r)
        item['company_name'] = names.get(r.get('company_id'), '—')
        result.append(item)
    return result


def index(request):
    return render(request, 'vacancies/index.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    error = None
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username'),
            password=request.POST.get('password'),
        )
        if user:
            login(request, user)
            return redirect('index')
        error = 'Неверный логин или пароль'
    return render(request, 'vacancies/login.html', {'error': error})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        if User.objects.filter(username=username).exists():
            error = 'Такой логин уже занят'
        elif Student.objects.filter(email=email).exists():
            error = 'Студент с таким email уже есть'
        else:
            try:
                user = User.objects.create_user(username=username, password=password, email=email)
                student = Student(
                    first_name=request.POST.get('first_name'),
                    last_name=request.POST.get('last_name'),
                    email=email,
                    phone=request.POST.get('phone', ''),
                    birth_date=request.POST.get('birth_date'),
                    course=int(request.POST.get('course', 1)),
                    specialty=request.POST.get('specialty'),
                )
                student.full_clean()
                student.save()
                login(request, user)
                return redirect('student_cabinet')
            except (ValidationError, ValueError) as e:
                error = str(e)
    return render(request, 'vacancies/register.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('index')


# --- студент: вакансии ---
@login_required
def vacancy_list(request):
    vacancies = annotate_vacancies(
        Vacancy.objects.select_related('company').all()
    )
    if not request.user.is_staff:
        vacancies = vacancies.filter(status='active')
    student = get_current_student(request)
    shortlist = get_shortlist_ids(request, student) if student else []
    return render(request, 'vacancies/vacancy_list.html', {
        'vacancies': vacancies,
        'shortlist': shortlist,
    })


@login_required
def vacancy_detail(request, pk):
    vacancy = get_object_or_404(
        annotate_vacancies(Vacancy.objects.select_related('company')),
        pk=pk,
    )
    student = get_current_student(request)
    shortlist = get_shortlist_ids(request, student) if student else []
    reviews = enrich_reviews([
        r for r in load_reviews()
        if r.get('is_approved') and r.get('company_id') == vacancy.company_id
    ])
    return render(request, 'vacancies/vacancy_detail.html', {
        'vacancy': vacancy,
        'is_student': student is not None,
        'is_favorite': pk in shortlist,
        'reviews': reviews,
    })


@student_required
def favorite_add(request, pk, student):
    vacancy = get_object_or_404(Vacancy, pk=pk)
    if vacancy.status != 'active':
        messages.error(request, 'Вакансия недоступна (не активна).')
        return redirect('vacancy_detail', pk=pk)
    key = f'shortlist_{student.id}'
    shortlist = request.session.get(key, [])
    if pk not in shortlist:
        shortlist.append(pk)
        add_shortlist_stat(pk)
    request.session[key] = shortlist
    return redirect('vacancy_detail', pk=pk)


@student_required
def favorite_remove(request, pk, student):
    key = f'shortlist_{student.id}'
    shortlist = request.session.get(key, [])
    if pk in shortlist:
        shortlist.remove(pk)
        remove_shortlist_stat(pk)
    request.session[key] = shortlist
    return redirect('favorites_list')


@student_required
def favorites_list(request, student):
    ids = get_shortlist_ids(request, student)
    vacancies = (
        annotate_vacancies(Vacancy.objects.filter(id__in=ids).select_related('company'))
        if ids else Vacancy.objects.none()
    )
    return render(request, 'vacancies/favorites_list.html', {'vacancies': vacancies})


@student_required
def application_add(request, vacancy_id, student):
    vacancy = get_object_or_404(Vacancy, pk=vacancy_id)
    resumes = student.resumes.filter(status='active')
    error = None
    if request.method == 'POST':
        resume_id = request.POST.get('resume')
        resume = resumes.filter(id=resume_id).first()
        if not resume:
            error = 'Выберите резюме'
        elif vacancy.status != 'active':
            error = 'Вакансия недоступна для отклика'
        elif Application.objects.filter(student=student, vacancy=vacancy).exists():
            error = 'Вы уже подавали заявку на эту вакансию'
        else:
            Application.objects.create(
                student=student,
                vacancy=vacancy,
                resume=resume,
                cover_letter=request.POST.get('cover_letter', ''),
                employer_comment='',
            )
            key = f'shortlist_{student.id}'
            shortlist = request.session.get(key, [])
            if vacancy_id in shortlist:
                shortlist.remove(vacancy_id)
                request.session[key] = shortlist
            return redirect('student_cabinet')
    return render(request, 'vacancies/application_form.html', {
        'vacancy': vacancy,
        'student': student,
        'resumes': resumes,
        'error': error,
    })


# --- студент: кабинет ---
@student_required
def student_cabinet(request, student):
    applications = student.applications.select_related('vacancy').all()
    resumes = student.resumes.all()
    ids = get_shortlist_ids(request, student)
    favorites = Vacancy.objects.filter(id__in=ids).select_related('company') if ids else Vacancy.objects.none()
    my_reviews = enrich_reviews([r for r in load_reviews() if r.get('student_id') == student.id])
    return render(request, 'vacancies/student_cabinet.html', {
        'student': student,
        'applications': applications,
        'resumes': resumes,
        'favorites': favorites,
        'reviews': my_reviews,
    })


@login_required
def student_form(request, pk=None):
    student = get_object_or_404(Student, pk=pk) if pk else None
    if not request.user.is_staff:
        current = get_current_student(request)
        if not student or not current or current.id != pk:
            return redirect('student_cabinet')
    error = None
    if request.method == 'POST':
        try:
            if not student:
                student = Student(
                    email=request.POST.get('email'),
                    birth_date=request.POST.get('birth_date'),
                )
            student.first_name = request.POST.get('first_name')
            student.last_name = request.POST.get('last_name')
            student.phone = request.POST.get('phone', '')
            student.course = int(request.POST.get('course', 1))
            student.specialty = request.POST.get('specialty')
            student.group = request.POST.get('group', '')
            student.faculty = request.POST.get('faculty', '')
            if request.user.is_staff:
                student.email = request.POST.get('email')
            student.full_clean()
            student.save()
            if request.user.is_staff:
                return redirect('student_list')
            return redirect('student_cabinet')
        except ValidationError as e:
            error = str(e)
    return render(request, 'vacancies/student_form.html', {'student': student, 'error': error})


@student_required
def resume_form(request, student, pk=None, student_id=None):
    if student_id is not None and student.id != student_id:
        return redirect('student_cabinet')
    resume = get_object_or_404(Resume, pk=pk, student=student) if pk else None
    error = None
    if request.method == 'POST':
        try:
            if resume:
                resume.title = request.POST.get('title')
                resume.experience = request.POST.get('experience')
                resume.education = request.POST.get('education', '')
                resume.contacts = request.POST.get('contacts')
                resume.skills_text = request.POST.get('skills_text', '')
                resume.status = request.POST.get('status', 'draft')
                resume.save()
            else:
                Resume.objects.create(
                    student=student,
                    title=request.POST.get('title', 'Основное резюме'),
                    experience=request.POST.get('experience'),
                    education=request.POST.get('education', ''),
                    contacts=request.POST.get('contacts'),
                    skills_text=request.POST.get('skills_text', ''),
                    status=request.POST.get('status', 'draft'),
                )
            return redirect('student_cabinet')
        except Exception as e:
            error = str(e)
    return render(request, 'vacancies/resume_form.html', {'resume': resume, 'error': error})


# --- студент: отзывы ---
@login_required
def review_list(request):
    reviews = load_reviews()
    if not request.user.is_staff:
        reviews = [r for r in reviews if r.get('is_approved')]
    company_id = request.GET.get('company')
    if company_id:
        reviews = [r for r in reviews if str(r.get('company_id')) == company_id]
    reviews = enrich_reviews(reviews)
    student = get_current_student(request)
    return render(request, 'vacancies/review_list.html', {
        'reviews': reviews,
        'companies': Company.objects.all(),
        'company_id': company_id or '',
        'is_student': student is not None,
    })


@student_required
def review_add(request, student):
    error = None
    companies = Company.objects.filter(
        id__in=Application.objects.filter(student=student).values_list('vacancy__company_id', flat=True)
    ).distinct()
    if request.method == 'POST':
        company_id = int(request.POST.get('company'))
        has_app = Application.objects.filter(student=student, vacancy__company_id=company_id).exists()
        if not has_app:
            error = 'Отзыв можно оставить только о компании, на вакансию которой вы подавали заявку'
        else:
            reviews = load_reviews()
            new_id = max([r.get('id', 0) for r in reviews], default=0) + 1
            reviews.append({
                'id': new_id,
                'student_id': student.id,
                'company_id': company_id,
                'rating': int(request.POST.get('rating', 5)),
                'text': request.POST.get('text'),
                'is_approved': False,
            })
            save_reviews(reviews)
            return redirect('student_cabinet')
    return render(request, 'vacancies/review_form.html', {'companies': companies, 'error': error})


# --- админ: вакансии и компании ---
@admin_required
def vacancy_form(request, pk=None):
    vacancy = get_object_or_404(Vacancy, pk=pk) if pk else None
    companies = Company.objects.all()
    error = None
    if request.method == 'POST':
        try:
            company = Company.objects.get(id=request.POST.get('company'))
            if vacancy:
                vacancy.company = company
                vacancy.title = request.POST.get('title')
                vacancy.description = request.POST.get('description')
                vacancy.requirements = request.POST.get('requirements', '')
                vacancy.salary = int(request.POST.get('salary'))
                vacancy.status = request.POST.get('status')
                vacancy.employment_type = request.POST.get('employment_type', 'full_time')
                vacancy.schedule = request.POST.get('schedule', '')
                vacancy.location = request.POST.get('location', '')
                vacancy.updated_by = request.user
                vacancy.save()
            else:
                Vacancy.objects.create(
                    title=request.POST.get('title'),
                    company=company,
                    description=request.POST.get('description'),
                    requirements=request.POST.get('requirements', ''),
                    salary=int(request.POST.get('salary')),
                    status=request.POST.get('status', 'active'),
                    employment_type=request.POST.get('employment_type', 'full_time'),
                    schedule=request.POST.get('schedule', ''),
                    location=request.POST.get('location', ''),
                    created_by=request.user,
                )
            return redirect('vacancy_list')
        except Exception as e:
            error = str(e)
    return render(request, 'vacancies/vacancy_form.html', {
        'vacancy': vacancy,
        'companies': companies,
        'error': error,
    })


@admin_required
def vacancy_delete(request, pk):
    get_object_or_404(Vacancy, pk=pk).delete()
    return redirect('vacancy_list')


@admin_required
def company_list(request):
    return render(request, 'vacancies/company_list.html', {
        'companies': Company.objects.all(),
    })


@admin_required
def company_form(request, pk=None):
    company = get_object_or_404(Company, pk=pk) if pk else None
    error = None
    if request.method == 'POST':
        try:
            if company:
                company.name = request.POST.get('name')
                company.email = request.POST.get('email')
                company.industry = request.POST.get('industry')
                company.description = request.POST.get('description', '')
                company.phone = request.POST.get('phone', '')
                company.address = request.POST.get('address', '')
                company.website = request.POST.get('website', '')
                company.size = request.POST.get('size', '')
            else:
                company = Company.objects.create(
                    name=request.POST.get('name'),
                    email=request.POST.get('email'),
                    industry=request.POST.get('industry'),
                    description=request.POST.get('description', ''),
                    phone=request.POST.get('phone', ''),
                    address=request.POST.get('address', ''),
                    website=request.POST.get('website', ''),
                    size=request.POST.get('size', ''),
                )
            if 'logo' in request.FILES:
                company.logo = request.FILES['logo']
                company.save()
            return redirect('company_list')
        except Exception as e:
            error = str(e)
    return render(request, 'vacancies/company_form.html', {'company': company, 'error': error})


@admin_required
def company_delete(request, pk):
    get_object_or_404(Company, pk=pk).delete()
    return redirect('company_list')


# --- админ: заявки и студенты ---
@admin_required
def application_list(request):
    applications = Application.objects.select_related(
        'student', 'vacancy', 'vacancy__company', 'resume'
    ).all()
    status_filter = request.GET.get('status')
    if status_filter:
        applications = applications.filter(status=status_filter)
    return render(request, 'vacancies/application_list.html', {
        'applications': applications,
        'status_choices': Application.STATUS_CHOICES,
        'status_filter': status_filter or '',
    })


@admin_required
def application_edit(request, pk):
    application = get_object_or_404(
        Application.objects.select_related('student', 'vacancy', 'vacancy__company', 'resume'),
        pk=pk,
    )
    if request.method == 'POST':
        application.status = request.POST.get('status')
        application.employer_comment = request.POST.get('employer_comment', '')
        application.response_date = timezone.now()
        application.save()
        return redirect('application_list')
    return render(request, 'vacancies/application_edit.html', {
        'application': application,
        'status_choices': Application.STATUS_CHOICES,
    })


@admin_required
def application_quick_status(request, pk, status):
    application = get_object_or_404(Application, pk=pk)
    allowed = [s[0] for s in Application.STATUS_CHOICES]
    if status in allowed:
        application.status = status
        application.response_date = timezone.now()
        application.save()
    return redirect('application_list')


@admin_required
def student_list(request):
    return render(request, 'vacancies/student_list.html', {
        'students': Student.objects.all(),
    })


@admin_required
def user_list(request):
    users = User.objects.all().order_by('username')
    return render(request, 'vacancies/user_list.html', {'users': users})


@admin_required
def user_toggle_active(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.id != request.user.id:
        user.is_active = not user.is_active
        user.save()
    return redirect('user_list')


@admin_required
def user_toggle_staff(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.id != request.user.id:
        user.is_staff = not user.is_staff
        user.save()
    return redirect('user_list')


# --- админ: отзывы и аналитика ---
@admin_required
def review_moderate_list(request):
    return render(request, 'vacancies/review_moderate_list.html', {
        'reviews': enrich_reviews(load_reviews()),
    })


@admin_required
def review_moderate(request, review_id, action):
    reviews = load_reviews()
    if action == 'approve':
        for r in reviews:
            if r.get('id') == review_id:
                r['is_approved'] = True
                break
    elif action == 'delete':
        reviews = [r for r in reviews if r.get('id') != review_id]
    save_reviews(reviews)
    return redirect('review_moderate_list')


@admin_required
def analytics(request):
    popular = Vacancy.objects.annotate(app_count=Count('applications')).order_by('-app_count')[:5]
    return render(request, 'vacancies/analytics.html', {
        'applications_total': Application.objects.count(),
        'active_vacancies': Vacancy.objects.filter(status='active').count(),
        'students_count': Student.objects.count(),
        'popular_vacancies': popular,
    })
