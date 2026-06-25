from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('staff-login/', views.staff_login_view, name='staff_login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.applicant_register, name='applicant_register'),
]