from django.db import models
from accounts.models import ApplicantProfile, ServiceOfficer


class ServiceCategory(models.Model):
    CATEGORY_CHOICES = [
        ('birth_certificate', 'Birth Certificate'),
        ('late_birth_certificate', 'Late Birth Certificate'),
        ('change_of_particulars', 'Change of Particulars'),
    ]

    name = models.CharField(max_length=50, choices=CATEGORY_CHOICES, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.get_name_display()


class Appointment(models.Model):
    applicant = models.ForeignKey(ApplicantProfile, on_delete=models.CASCADE, related_name='appointments')
    service_category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='appointments')
    huduma_booking_ref = models.CharField(max_length=100, unique=True)
    appointment_date = models.DateField()
    appointment_time = models.TimeField()

    STATUS_CHOICES = [
        ('booked', 'Booked'),
        ('attended', 'Attended'),
        ('missed', 'Missed'),
    ]
    booking_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='booked')

    def __str__(self):
        return f"{self.applicant.full_name} - {self.huduma_booking_ref}"


class Application(models.Model):
    applicant = models.ForeignKey(ApplicantProfile, on_delete=models.CASCADE, related_name='applications')
    service_category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='applications')
    ecitizen_application_ref = models.CharField(max_length=100, unique=True)

    DOCUMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('complete', 'Complete'),
        ('incomplete', 'Incomplete'),
    ]
    document_status = models.CharField(max_length=20, choices=DOCUMENT_STATUS_CHOICES, default='pending')

    PROCESSING_STATUS_CHOICES = [
        ('not_started', 'Not Started'),
        ('under_review', 'Under Review'),
        ('processed', 'Processed'),
    ]
    processing_status = models.CharField(max_length=20, choices=PROCESSING_STATUS_CHOICES, default='not_started')

    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.ecitizen_application_ref


class QueueTicket(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name='queue_ticket')
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='queue_tickets')
    applicant = models.ForeignKey(ApplicantProfile, on_delete=models.CASCADE, related_name='queue_tickets')

    ticket_number = models.CharField(max_length=20, unique=True)

    STATUS_CHOICES = [
        ('tracking', 'Tracking'),
        ('waiting', 'Waiting'),
        ('called', 'Called'),
        ('in_service', 'In Service'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
    ]
    current_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='tracking')

    arrival_confirmed = models.BooleanField(default=False)
    joined_queue_at = models.DateTimeField(blank=True, null=True)
    estimated_wait_minutes = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.ticket_number


class QueueStatusHistory(models.Model):
    queue_ticket = models.ForeignKey(QueueTicket, on_delete=models.CASCADE, related_name='status_history')
    updated_by = models.ForeignKey(ServiceOfficer, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20)
    notes = models.TextField(blank=True, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.queue_ticket.ticket_number} - {self.status}"