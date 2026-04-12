from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('call/<int:ticket_id>/', views.call_next, name='call_next'),
    path('start/<int:ticket_id>/', views.start_service, name='start_service'),
    path('complete/<int:ticket_id>/', views.complete_service, name='complete_service'),
    path('queue-data/', views.staff_queue_data, name='staff_queue_data'),
]