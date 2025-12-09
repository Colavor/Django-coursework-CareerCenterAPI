from django.shortcuts import render

def vacancies(request):
    return render(request, 'vacancies/vacancies.html')
