from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.reports_dashboard, name='reports_dashboard'),
]