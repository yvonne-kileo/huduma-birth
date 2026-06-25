from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('applications/', views.application_review_list, name='application_review_list'),
    path('applications/<int:application_id>/update/', views.application_review_update, name='application_review_update'),
    path('applications/<int:application_id>/action/<str:action>/', views.application_review_action, name='application_review_action'),
    path('call/<int:ticket_id>/', views.call_next, name='call_next'),
    path('start/<int:ticket_id>/', views.start_service, name='start_service'),
    path('complete/<int:ticket_id>/', views.complete_service, name='complete_service'),
    path('queue-data/', views.staff_queue_data, name='staff_queue_data'),
    
]