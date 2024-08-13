# Create your views here.
def home(request):
    from django.shortcuts import render
    return render(request, '../templates/home.html')