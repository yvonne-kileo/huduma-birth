from django.contrib import admin
from .models import (
    ServiceCategory,
    Appointment,
    Application,
    QueueTicket,
    QueueStatusHistory,
)


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = (
        'applicant',
        'service_category',
        'huduma_booking_ref',
        'appointment_date',
        'appointment_time',
        'booking_status',
    )
    list_filter = ('service_category', 'booking_status', 'appointment_date')
    search_fields = ('applicant__full_name', 'huduma_booking_ref')


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'applicant',
        'service_category',
        'ecitizen_application_ref',
        'document_status',
        'processing_status',
        'submitted_at',
    )
    list_filter = ('service_category', 'document_status', 'processing_status')
    search_fields = ('applicant__full_name', 'ecitizen_application_ref')


@admin.register(QueueTicket)
class QueueTicketAdmin(admin.ModelAdmin):
    list_display = (
        'ticket_number',
        'applicant',
        'appointment',
        'current_status',
        'arrival_confirmed',
        'estimated_wait_minutes',
    )
    list_filter = ('current_status', 'arrival_confirmed')
    search_fields = ('ticket_number', 'applicant__full_name')


@admin.register(QueueStatusHistory)
class QueueStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ('queue_ticket', 'status', 'updated_by', 'changed_at')
    list_filter = ('status', 'changed_at')
    search_fields = ('queue_ticket__ticket_number',)