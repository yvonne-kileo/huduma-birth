from django.urls import path
from . import views

urlpatterns = [
    path('ecitizen/login/', views.ecitizen_login_view, name='ecitizen_login'),
    path('ecitizen/crs-services/', views.crs_service_selection, name='crs_service_selection'),
    path('ecitizen/apply/', views.ecitizen_application_create, name='ecitizen_application_create'),
    path('ecitizen/payment/', views.ecitizen_payment, name='ecitizen_payment'),
    path('ecitizen/success/<int:application_id>/', views.ecitizen_application_success, name='ecitizen_application_success'),

    path('huduma/login/', views.huduma_login_view, name='huduma_login'),
    path('huduma/book/', views.huduma_booking_create, name='huduma_booking_create'),
    path('huduma/success/<int:appointment_id>/', views.huduma_booking_success, name='huduma_booking_success'),
]