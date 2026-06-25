from django.urls import path
from . import views

urlpatterns = [
    path('notifications/', views.applicant_notifications, name='applicant_notifications'),
    path('notifications/read/', views.mark_notifications_read, name='mark_notifications_read'),
    path('ecitizen/login/', views.ecitizen_login_view, name='ecitizen_login'),
    path('ecitizen/instructions/', views.ecitizen_birth_instructions, name='ecitizen_birth_instructions'),
    path('ecitizen/application-details/', views.ecitizen_application_details, name='ecitizen_application_details'),
    path('ecitizen/child-details/', views.ecitizen_child_details, name='ecitizen_child_details'),
    path('ecitizen/parents-information/', views.ecitizen_parents_information, name='ecitizen_parents_information'),
    path('ecitizen/uploads/', views.ecitizen_uploads, name='ecitizen_uploads'),
    path('ecitizen/review-payment/', views.ecitizen_review_payment, name='ecitizen_review_payment'),
    path('ecitizen/success/<int:application_id>/', views.ecitizen_application_success, name='ecitizen_application_success'),

    path('huduma/login/', views.huduma_login_view, name='huduma_login'),
    path('huduma/book/', views.huduma_booking_create, name='huduma_booking_create'),
    path('huduma/success/<int:appointment_id>/', views.huduma_booking_success, name='huduma_booking_success'),
]