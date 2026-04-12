from django.db import models
from django.contrib.auth.models import User


class ApplicantProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='applicant_profile')
    full_name = models.CharField(max_length=150)
    national_id = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField()

    def __str__(self):
        return self.full_name


class ServiceOfficer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='service_officer_profile')
    full_name = models.CharField(max_length=150)
    staff_id = models.CharField(max_length=20, unique=True)
    counter_number = models.CharField(max_length=20)
    role = models.CharField(max_length=100, default='Service Officer')

    def __str__(self):
        return f"{self.full_name} - Counter {self.counter_number}"