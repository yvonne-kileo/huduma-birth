from django.contrib import admin
from .models import ApplicantProfile, ServiceOfficer


@admin.register(ApplicantProfile)
class ApplicantProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'national_id', 'phone_number', 'email')
    search_fields = ('full_name', 'national_id', 'phone_number', 'email')


@admin.register(ServiceOfficer)
class ServiceOfficerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'staff_id', 'counter_number', 'role')
    search_fields = ('full_name', 'staff_id', 'counter_number', 'role')