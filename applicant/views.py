from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from queueing.models import Appointment, Application, QueueTicket, QueueStatusHistory, Notification


AVERAGE_SERVICE_MINUTES = 10


def generate_ticket_number():
    latest_ticket = QueueTicket.objects.order_by('-id').first()
    next_id = 1 if latest_ticket is None else latest_ticket.id + 1
    return f"TKT{next_id:04d}"


def get_applicant_stage(application, appointment):
    if not application:
        return 'not_started'

    if application.processing_status == 'rejected':
        return 'rejected'

    if application.document_status == 'incomplete':
        return 'incomplete'

    if application.processing_status == 'under_review':
        return 'under_review'

    if application.document_status == 'verified' or application.processing_status in ['processed', 'approved']:
        if appointment:
            return 'ready_for_appointment'
        return 'verified'

    if application.processing_status == 'submitted':
        return 'submitted'

    return 'not_started'


def get_active_queue_queryset(queue_ticket):
    """
    Active queue for the same appointment date and same service category.
    Only applicants who confirmed arrival should be in the queue.
    """
    if not queue_ticket or not queue_ticket.appointment:
        return QueueTicket.objects.none()

    appointment = queue_ticket.appointment

    return QueueTicket.objects.filter(
        appointment__appointment_date=appointment.appointment_date,
        appointment__service_category=appointment.service_category,
        arrival_confirmed=True,
        current_status__in=['waiting', 'called', 'in_service'],
    ).order_by('joined_queue_at', 'id')

def get_application_display_code(application, field_names, prefix):
    if not application:
        return '-'

    for field_name in field_names:
        value = getattr(application, field_name, None)

        if value is not None and value != '':
            return str(value)

    reference = getattr(application, 'ecitizen_application_ref', '')

    digits = ''.join([character for character in str(reference) if character.isdigit()])

    if not digits:
        digits = f'{application.id:08d}'

    return f'{prefix}{digits}'
@login_required
def applicant_dashboard(request):
    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'You do not have applicant access.')
        return redirect('login')

    applicant = request.user.applicant_profile

    appointment = Appointment.objects.filter(applicant=applicant).order_by(
        '-appointment_date', '-appointment_time'
    ).first()

    application = Application.objects.filter(applicant=applicant).order_by(
        '-submitted_at'
    ).first()

    queue_ticket = QueueTicket.objects.filter(applicant=applicant).order_by('-id').first()

    application_stage = get_applicant_stage(application, appointment)

    invoice_number = get_application_display_code(
    application,
    ['invoice_number', 'invoice_no', 'ecitizen_invoice_number', 'application_invoice_number'],
    'INV'
)

    receipt_number = get_application_display_code(
    application,
    ['receipt_number', 'receipt_no', 'ecitizen_receipt_number', 'payment_receipt_number'],
    'RCT'
)

    queue_position = None
    people_ahead = 0

    if queue_ticket and queue_ticket.arrival_confirmed and queue_ticket.current_status in ['waiting', 'called', 'in_service']:
        active_queue = list(get_active_queue_queryset(queue_ticket))

        for index, ticket in enumerate(active_queue):
            if ticket.id == queue_ticket.id:
                queue_position = index + 1
                people_ahead = index
                break

        if queue_ticket.current_status == 'waiting':
            queue_ticket.estimated_wait_minutes = people_ahead * AVERAGE_SERVICE_MINUTES
            queue_ticket.save(update_fields=['estimated_wait_minutes'])

    context = {
        'applicant': applicant,
        'appointment': appointment,
        'application': application,
        'queue_ticket': queue_ticket,
        'application_stage': application_stage,
        'queue_position': queue_position,
        'people_ahead': people_ahead,
        'invoice_number': invoice_number,
        'receipt_number': receipt_number,
    }

    return render(request, 'applicant/dashboard.html', context)


@login_required
def confirm_arrival(request, ticket_id):
    if request.method != 'POST':
        return redirect('applicant_dashboard')

    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'You do not have applicant access.')
        return redirect('login')

    applicant = request.user.applicant_profile
    ticket = get_object_or_404(QueueTicket, id=ticket_id, applicant=applicant)

    if ticket.arrival_confirmed:
        messages.info(request, 'Arrival already confirmed.')
        return redirect('applicant_dashboard')

    if not ticket.appointment:
        messages.error(request, 'No appointment found for this ticket.')
        return redirect('applicant_dashboard')

    today = timezone.localdate()
    appointment_date = ticket.appointment.appointment_date

    if today < appointment_date:
        messages.error(request, 'You can only confirm arrival on your appointment date.')
        return redirect('applicant_dashboard')

    if today > appointment_date:
        messages.error(request, 'This appointment date has already passed.')
        return redirect('applicant_dashboard')

    ticket.arrival_confirmed = True
    ticket.current_status = 'waiting'
    ticket.joined_queue_at = timezone.now()
    ticket.save()

    QueueStatusHistory.objects.create(
        queue_ticket=ticket,
        updated_by=None,
        status='waiting',
        notes='Applicant confirmed arrival.'
    )

    messages.success(request, 'Arrival confirmed.')
    return redirect('applicant_dashboard')

def create_queue_milestone_notification(ticket, position, people_ahead):
    if not ticket or not ticket.applicant:
        return

    if not position:
        return

    if ticket.current_status != 'waiting':
        return

    milestone = None
    title = ''
    message = ''

    if position == 1:
        milestone = 'next'
        title = 'You are next'
        message = 'You are next in line. Please stay ready and wait to be called.'

    elif position <= 3:
        milestone = 'top-3'
        title = 'You are almost at the counter'
        message = f'You are number {position} in the queue. Please stay nearby.'

    elif position <= 5:
        milestone = 'top-5'
        title = 'Queue moving'
        message = f'You are now in the top 5. There are {people_ahead} applicant(s) ahead of you.'

    elif position <= 10:
        milestone = 'top-10'
        title = 'Queue update'
        message = f'You are now in the top 10. There are {people_ahead} applicant(s) ahead of you.'

    else:
        milestone = 'initial-position'
        title = 'Queue position confirmed'
        message = f'You are number {position} in the queue. There are {people_ahead} applicant(s) ahead of you.'

    metadata_key = f'queue-{milestone}-{ticket.id}'

    Notification.objects.get_or_create(
        applicant=ticket.applicant,
        metadata_key=metadata_key,
        defaults={
            'notification_type': 'queue',
            'title': title,
            'message': message,
            'is_read': False,
        }
    )
@login_required
def applicant_queue_status(request):
    if not hasattr(request.user, 'applicant_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    applicant = request.user.applicant_profile
    queue_ticket = QueueTicket.objects.filter(applicant=applicant).order_by('-id').first()

    if not queue_ticket:
        return JsonResponse({'error': 'No queue ticket found'}, status=404)

    active_queue = list(get_active_queue_queryset(queue_ticket))

    position = None
    people_ahead = 0
    queue_list = []

    if queue_ticket.arrival_confirmed and queue_ticket.current_status in ['waiting', 'called', 'in_service']:
        for index, ticket in enumerate(active_queue):
            queue_list.append({
                'id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'is_me': ticket.id == queue_ticket.id,
            })

            if ticket.id == queue_ticket.id:
                position = index + 1
                people_ahead = index

    create_queue_milestone_notification(queue_ticket, position, people_ahead)

    if queue_ticket.current_status == 'waiting' and queue_ticket.arrival_confirmed:
        estimated_wait = people_ahead * AVERAGE_SERVICE_MINUTES
    elif queue_ticket.current_status == 'called':
        estimated_wait = 1
    elif queue_ticket.current_status == 'in_service':
        estimated_wait = 0
    elif queue_ticket.current_status == 'completed':
        estimated_wait = 0
    else:
        estimated_wait = queue_ticket.estimated_wait_minutes or 0

    if queue_ticket.estimated_wait_minutes != estimated_wait:
        queue_ticket.estimated_wait_minutes = estimated_wait
        queue_ticket.save(update_fields=['estimated_wait_minutes'])

    data = {
        'ticket_number': queue_ticket.ticket_number,
        'current_status': queue_ticket.current_status,
        'current_status_display': queue_ticket.get_current_status_display(),
        'arrival_confirmed': queue_ticket.arrival_confirmed,
        'estimated_wait_minutes': estimated_wait,
        'position': position,
        'people_ahead': people_ahead,
        'queue_total': len(active_queue),
        'queue_list': queue_list,
        'large_queue_mode': len(active_queue) > 10,
    }

    return JsonResponse(data)


@login_required
def applicant_notifications(request):
    if not hasattr(request.user, 'applicant_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    applicant = request.user.applicant_profile

    notifications = Notification.objects.filter(applicant=applicant).order_by('-created_at')[:20]
    unread_count = Notification.objects.filter(applicant=applicant, is_read=False).count()

    notification_list = []

    for notification in notifications:
        notification_list.append({
            'id': notification.id,
            'title': notification.title,
            'message': notification.message,
            'type': notification.notification_type,
            'is_read': notification.is_read,
            'link': notification.link,
            'created_at': notification.created_at.strftime('%d %b %Y, %I:%M %p'),
        })

    return JsonResponse({
        'notifications': notification_list,
        'unread_count': unread_count,
    })


@login_required
@require_POST
def mark_notifications_read(request):
    if not hasattr(request.user, 'applicant_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    applicant = request.user.applicant_profile

    Notification.objects.filter(
        applicant=applicant,
        is_read=False
    ).update(is_read=True)

    return JsonResponse({'success': True})


@login_required
def download_application_invoice(request, application_id):
    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'You do not have applicant access.')
        return redirect('login')

    applicant = request.user.applicant_profile

    application = get_object_or_404(
        Application,
        id=application_id,
        applicant=applicant
    )

    appointment = Appointment.objects.filter(
        applicant=applicant
    ).order_by('-appointment_date', '-appointment_time').first()

    def first_existing_value(obj, field_names, default='-'):
        for field_name in field_names:
            value = getattr(obj, field_name, None)

            if value is not None and value != '':
                return str(value)

        return default

    def safe_value(obj, field_name, default='-'):
        value = getattr(obj, field_name, default)

        if value is None or value == '':
            return default

        return str(value)

    def safe_date(value):
        if not value:
            return '-'

        try:
            return value.strftime('%d %B %Y, %I:%M %p')
        except Exception:
            return str(value)

    def uploaded_status(file_field):
        if file_field:
            return 'Uploaded'
        return 'Not Uploaded'

    ecitizen_ref = safe_value(application, 'ecitizen_application_ref', f'ECIT{application.id:08d}')

    digits = ''.join([character for character in ecitizen_ref if character.isdigit()])
    if not digits:
        digits = f'{application.id:08d}'

    invoice_number = first_existing_value(
        application,
        ['invoice_number', 'invoice_no', 'ecitizen_invoice_number', 'application_invoice_number'],
        default=f'INV{digits}'
    )

    receipt_number = first_existing_value(
        application,
        ['receipt_number', 'receipt_no', 'ecitizen_receipt_number', 'payment_receipt_number'],
        default=f'RCT{digits}'
    )

    transaction_code = first_existing_value(
        application,
        ['transaction_code', 'mpesa_code', 'payment_code', 'payment_reference'],
        default=f'TXN{digits}'
    )

    payment_method = first_existing_value(
        application,
        ['payment_method', 'payment_mode', 'mode_of_payment'],
        default='M-Pesa Simulation'
    )

    payment_phone = first_existing_value(
        application,
        ['payment_phone', 'phone_used_for_payment', 'mpesa_phone'],
        default=safe_value(applicant, 'phone_number')
    )

    amount_paid = first_existing_value(
        application,
        ['amount_paid', 'payment_amount', 'amount', 'fee_amount'],
        default='-'
    )

    child_name = ' '.join([
        safe_value(application, 'child_first_name', ''),
        safe_value(application, 'child_middle_name', ''),
        safe_value(application, 'child_last_name', ''),
    ]).strip()

    if not child_name:
        child_name = '-'

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=38,
        bottomMargin=38
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Title'],
        fontSize=21,
        leading=25,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#007a4d'),
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        'InvoiceSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#667085'),
        spaceAfter=18,
    )

    section_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#101828'),
        spaceBefore=12,
        spaceAfter=7,
    )

    label_style = ParagraphStyle(
        'LabelCell',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#344054'),
        fontName='Helvetica-Bold',
    )

    value_style = ParagraphStyle(
        'ValueCell',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#344054'),
    )

    elements = []

    elements.append(Paragraph('eCitizen Birth Certificate Invoice', title_style))
    elements.append(Paragraph('Application and Payment Confirmation', subtitle_style))

    invoice_data = [
        ['eCitizen Application Reference', ecitizen_ref],
        ['Invoice Number', invoice_number],
        ['Receipt Number', receipt_number],
        ['Transaction Code', transaction_code],
        ['Submitted At', safe_date(getattr(application, 'submitted_at', None))],
    ]

    payment_data = [
        ['Payment Method', payment_method],
        ['Payment Phone', payment_phone],
        ['Amount Paid', amount_paid],
        ['Payment Status', 'Paid'],
    ]

    applicant_data = [
        ['Applicant Name', safe_value(applicant, 'full_name')],
        ['National ID', safe_value(applicant, 'national_id')],
        ['Phone Number', safe_value(applicant, 'phone_number')],
        ['Email Address', safe_value(applicant, 'email')],
    ]

    application_data = [
        ['Application Title', safe_value(application, 'application_title')],
        ['Type of Application', safe_value(application, 'type_of_application')],
        ['Pickup Location', safe_value(application, 'pickup_location')],
        ['Residential Address', safe_value(application, 'residential_address')],
        ['Child Over 18', safe_value(application, 'child_over_18')],
        ['Born in Health Facility', safe_value(application, 'born_in_health_facility')],
        ['County of Birth', safe_value(application, 'county_of_birth')],
        ['Notification Number', safe_value(application, 'notification_number')],
        ['Child Name', child_name],
        ['Date of Birth', safe_value(application, 'date_of_birth')],
        ['Sex', safe_value(application, 'sex')],
    ]

    parent_data = [
        ['Father Full Name', safe_value(application, 'father_full_name')],
        ['Father ID Number', safe_value(application, 'father_id_number')],
        ['Mother Full Name', safe_value(application, 'mother_full_name')],
        ['Mother ID Number', safe_value(application, 'mother_id_number')],
        ['Parent / Guardian Phone', safe_value(application, 'parent_phone_number')],
    ]

    document_data = [
        ['Birth Notification', uploaded_status(getattr(application, 'upload_birth_notification', None))],
        ['Applicant ID', uploaded_status(getattr(application, 'upload_applicant_id', None))],
        ['Parent ID', uploaded_status(getattr(application, 'upload_parent_id', None))],
        ['Document Status', safe_value(application, 'document_status')],
        ['Processing Status', safe_value(application, 'processing_status')],
    ]

    appointment_data = [
        ['Huduma Booking Reference', safe_value(appointment, 'huduma_booking_ref') if appointment else '-'],
        ['Huduma Centre', 'Huduma Centre City Square' if appointment else '-'],
        ['Appointment Date', safe_value(appointment, 'appointment_date') if appointment else '-'],
        ['Appointment Time', safe_value(appointment, 'appointment_time') if appointment else '-'],
        ['Booking Status', safe_value(appointment, 'booking_status') if appointment else '-'],
    ]

    def make_table(data):
        formatted_data = []

        for label, value in data:
            formatted_data.append([
                Paragraph(str(label), label_style),
                Paragraph(str(value), value_style),
            ])

        table = Table(formatted_data, colWidths=[180, 300])

        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f6f8fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e7edf0')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))

        return table

    elements.append(Paragraph('Invoice Details', section_style))
    elements.append(make_table(invoice_data))

    elements.append(Paragraph('Payment Details', section_style))
    elements.append(make_table(payment_data))

    elements.append(Paragraph('Applicant Details', section_style))
    elements.append(make_table(applicant_data))

    elements.append(Paragraph('Birth Certificate Application Details', section_style))
    elements.append(make_table(application_data))

    elements.append(Paragraph('Parent / Guardian Details', section_style))
    elements.append(make_table(parent_data))

    elements.append(Paragraph('Uploaded Documents', section_style))
    elements.append(make_table(document_data))

    elements.append(Paragraph('Huduma Appointment Details', section_style))
    elements.append(make_table(appointment_data))

    doc.build(elements)

    pdf = buffer.getvalue()
    buffer.close()

    filename = f'{ecitizen_ref}_invoice.pdf'.replace(' ', '_').replace('/', '_')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.write(pdf)

    return response