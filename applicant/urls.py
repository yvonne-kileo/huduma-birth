from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.applicant_dashboard, name='applicant_dashboard'),
    path('confirm-arrival/<int:ticket_id>/', views.confirm_arrival, name='confirm_arrival'),
    path('queue-status/', views.applicant_queue_status, name='applicant_queue_status'),
]