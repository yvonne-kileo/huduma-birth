from django.db import models
from accounts.models import ApplicantProfile, ServiceOfficer


class ServiceCategory(models.Model):
    CATEGORY_CHOICES = [
        ('birth_certificate', 'Birth Certificate'),
    ]

    name = models.CharField(max_length=100, choices=CATEGORY_CHOICES, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.get_name_display()


class Appointment(models.Model):
    applicant = models.ForeignKey(
        ApplicantProfile,
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    service_category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.CASCADE,
        related_name='appointments'
    )
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
    TYPE_OF_APPLICATION_CHOICES = [
        ('without_amendment', 'Application for Birth Certificate without Amendment'),
        ('with_amendment', 'Application for Birth Certificate with Amendment'),
    ]

    YES_NO_CHOICES = [
        ('yes', 'YES'),
        ('no', 'NO'),
    ]

    SEX_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
    ]

    applicant = models.ForeignKey(
        ApplicantProfile,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    service_category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    ecitizen_application_ref = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True
    )

    # Instructions / title
    application_title = models.CharField(
        max_length=200,
        default='Application for Current Birth Certificate'
    )

    # Step 2: Application Details
    type_of_application = models.CharField(
        max_length=50,
        choices=TYPE_OF_APPLICATION_CHOICES,
        blank=True,
        null=True
    )
    amendment_name_of_child = models.BooleanField(default=False)
    amendment_place_of_birth = models.BooleanField(default=False)
    amendment_name_of_mother = models.BooleanField(default=False)
    amendment_name_of_father = models.BooleanField(default=False)
    amendment_other = models.BooleanField(default=False)
    pickup_location = models.CharField(max_length=150, blank=True, null=True)
    residential_address = models.CharField(max_length=255, blank=True, null=True)

    # Step 3: Child Details
    child_over_18 = models.CharField(
        max_length=10,
        choices=YES_NO_CHOICES,
        blank=True,
        null=True
    )
    born_in_health_facility = models.CharField(
        max_length=10,
        choices=YES_NO_CHOICES,
        blank=True,
        null=True
    )
    county_of_birth = models.CharField(max_length=100, blank=True, null=True)
    notification_number = models.CharField(max_length=100, blank=True, null=True)
    child_first_name = models.CharField(max_length=100, blank=True, null=True)
    child_middle_name = models.CharField(max_length=100, blank=True, null=True)
    child_last_name = models.CharField(max_length=100, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    sex = models.CharField(
        max_length=20,
        choices=SEX_CHOICES,
        blank=True,
        null=True
    )

    # Step 4: Parents' Information
    father_full_name = models.CharField(max_length=200, blank=True, null=True)
    father_id_number = models.CharField(max_length=50, blank=True, null=True)
    mother_full_name = models.CharField(max_length=200, blank=True, null=True)
    mother_id_number = models.CharField(max_length=50, blank=True, null=True)
    parent_phone_number = models.CharField(max_length=30, blank=True, null=True)

    # Step 5: Uploads
    upload_birth_notification = models.FileField(upload_to='uploads/birth_notifications/', blank=True, null=True)
    upload_applicant_id = models.FileField(upload_to='uploads/applicant_ids/', blank=True, null=True)
    upload_parent_id = models.FileField(upload_to='uploads/parent_ids/', blank=True, null=True)

    DOCUMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('complete', 'Complete'),
        ('incomplete', 'Incomplete'),
        ('verified', 'Verified'),
    ]
    document_status = models.CharField(
        max_length=20,
        choices=DOCUMENT_STATUS_CHOICES,
        default='pending'
    )

    PROCESSING_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('processed', 'Processed'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default='draft'
    )

    submitted_at = models.DateTimeField(auto_now_add=True)
    review_notes = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.ecitizen_application_ref or f"Draft - {self.applicant.full_name}"


class QueueTicket(models.Model):
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='queue_ticket'
    )
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='queue_tickets'
    )
    applicant = models.ForeignKey(
        ApplicantProfile,
        on_delete=models.CASCADE,
        related_name='queue_tickets'
    )

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
    queue_ticket = models.ForeignKey(
        QueueTicket,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    updated_by = models.ForeignKey(
        ServiceOfficer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    status = models.CharField(max_length=20)
    notes = models.TextField(blank=True, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.queue_ticket.ticket_number} - {self.status}"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('queue', 'Queue Update'),
        ('application', 'Application Update'),
        ('collection', 'Collection Update'),
        ('system', 'System Message'),
    ]

    applicant = models.ForeignKey(
        'accounts.ApplicantProfile',
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NOTIFICATION_TYPES,
        default='system'
    )
    title = models.CharField(max_length=150)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    metadata_key = models.CharField(max_length=150, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.applicant.full_name} - {self.title}"