from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Max
from .models import Notification
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import ServiceCategory, Application, Appointment, QueueTicket

def create_notification(applicant, title, message, notification_type='system', link='', metadata_key=''):
    if metadata_key:
        existing_notification = Notification.objects.filter(
            applicant=applicant,
            metadata_key=metadata_key
        ).first()

        if existing_notification:
            existing_notification.title = title
            existing_notification.message = message
            existing_notification.notification_type = notification_type
            existing_notification.link = link
            existing_notification.is_read = False
            existing_notification.save()
            return existing_notification

    return Notification.objects.create(
        applicant=applicant,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
        metadata_key=metadata_key
    )

def generate_ecitizen_reference():
    latest_application = Application.objects.aggregate(max_id=Max('id'))
    next_id = (latest_application['max_id'] or 0) + 1
    return f"ECIT2026{next_id:04d}"


def generate_invoice_number():
    latest_application = Application.objects.aggregate(max_id=Max('id'))
    next_id = (latest_application['max_id'] or 0) + 1
    return f"INV2026{next_id:04d}"


def generate_receipt_number():
    latest_application = Application.objects.aggregate(max_id=Max('id'))
    next_id = (latest_application['max_id'] or 0) + 1
    return f"RCT2026{next_id:04d}"


def generate_huduma_booking_reference():
    latest_appointment = Appointment.objects.aggregate(max_id=Max('id'))
    next_id = (latest_appointment['max_id'] or 0) + 1
    return f"HUD2026{next_id:04d}"

def generate_ticket_number():
    latest_ticket = QueueTicket.objects.order_by('-id').first()
    next_id = 1 if latest_ticket is None else latest_ticket.id + 1
    return f"TKT{next_id:04d}"


def get_birth_certificate_category():
    category = ServiceCategory.objects.filter(name='birth_certificate').first()
    if category:
        return category

    return ServiceCategory.objects.create(
        name='birth_certificate',
        description='Birth Certificate Service'
    )


def get_or_create_draft_application(applicant):
    application = (
        Application.objects.filter(
            applicant=applicant,
            service_category__name='birth_certificate',
            processing_status='draft',
        )
        .order_by('-id')
        .first()
    )

    if application:
        return application

    return Application.objects.create(
        applicant=applicant,
        service_category=get_birth_certificate_category(),
        application_title='Application for Current Birth Certificate',
        processing_status='draft',
        document_status='pending',
    )


@login_required
def ecitizen_login_view(request):
    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'Only applicants can access the eCitizen simulation.')
        return redirect('login')

    applicant = request.user.applicant_profile

    if request.method == 'POST':
        national_id = request.POST.get('national_id', '').strip()
        password = request.POST.get('password', '').strip()

        if national_id != applicant.national_id:
            messages.error(request, 'National ID does not match the logged-in applicant.')
            return redirect('ecitizen_login')

        if password != 'ecitizen123':
            messages.error(request, 'Invalid eCitizen password.')
            return redirect('ecitizen_login')

        request.session['ecitizen_verified'] = True
        messages.success(request, 'eCitizen login successful.')
        return redirect('ecitizen_birth_instructions')

    context = {
        'applicant': applicant,
    }
    return render(request, 'queueing/ecitizen_login.html', context)


@login_required
def ecitizen_birth_instructions(request):
    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'Only applicants can access the eCitizen simulation.')
        return redirect('login')

    if not request.session.get('ecitizen_verified'):
        messages.error(request, 'Please log in through the eCitizen simulation first.')
        return redirect('ecitizen_login')

    applicant = request.user.applicant_profile
    application = get_or_create_draft_application(applicant)

    if request.method == 'POST':
        return redirect('ecitizen_application_details')

    context = {
        'application': application,
    }
    return render(request, 'queueing/ecitizen_birth_instructions.html', context)


@login_required
def ecitizen_application_details(request):
    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'Only applicants can access the eCitizen simulation.')
        return redirect('login')

    if not request.session.get('ecitizen_verified'):
        messages.error(request, 'Please log in through the eCitizen simulation first.')
        return redirect('ecitizen_login')

    applicant = request.user.applicant_profile
    application = get_or_create_draft_application(applicant)

    if request.method == 'POST':
        type_of_application = request.POST.get('type_of_application', '').strip()
        pickup_location = request.POST.get('pickup_location', '').strip()
        residential_address = request.POST.get('residential_address', '').strip()

        if not type_of_application:
            messages.error(request, 'Please select the type of application.')
            return redirect('ecitizen_application_details')

        if not pickup_location:
            messages.error(request, 'Please select a pickup location.')
            return redirect('ecitizen_application_details')

        if not residential_address:
            messages.error(request, 'Please enter the residential address.')
            return redirect('ecitizen_application_details')

        application.type_of_application = type_of_application

        if type_of_application == 'with_amendment':
            application.amendment_name_of_child = bool(request.POST.get('amendment_name_of_child'))
            application.amendment_place_of_birth = bool(request.POST.get('amendment_place_of_birth'))
            application.amendment_name_of_mother = bool(request.POST.get('amendment_name_of_mother'))
            application.amendment_name_of_father = bool(request.POST.get('amendment_name_of_father'))
            application.amendment_other = bool(request.POST.get('amendment_other'))

            if not any([
                application.amendment_name_of_child,
                application.amendment_place_of_birth,
                application.amendment_name_of_mother,
                application.amendment_name_of_father,
                application.amendment_other,
            ]):
                messages.error(request, 'Please select at least one amendment type.')
                return redirect('ecitizen_application_details')
        else:
            application.amendment_name_of_child = False
            application.amendment_place_of_birth = False
            application.amendment_name_of_mother = False
            application.amendment_name_of_father = False
            application.amendment_other = False

        application.pickup_location = pickup_location
        application.residential_address = residential_address
        application.save()

        return redirect('ecitizen_child_details')

    context = {
        'application': application,
    }
    return render(request, 'queueing/ecitizen_application_details.html', context)
        

    context = {
        'application': application,
    }
    return render(request, 'queueing/ecitizen_application_details.html', context)


@login_required
def ecitizen_child_details(request):
    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'Only applicants can access the eCitizen simulation.')
        return redirect('login')

    if not request.session.get('ecitizen_verified'):
        messages.error(request, 'Please log in through the eCitizen simulation first.')
        return redirect('ecitizen_login')

    applicant = request.user.applicant_profile
    application = get_or_create_draft_application(applicant)

    if request.method == 'POST':
        child_over_18 = request.POST.get('child_over_18', '').strip()
        born_in_health_facility = request.POST.get('born_in_health_facility', '').strip()
        county_of_birth = request.POST.get('county_of_birth', '').strip()
        notification_number = request.POST.get('notification_number', '').strip()
        child_first_name = request.POST.get('child_first_name', '').strip()
        child_middle_name = request.POST.get('child_middle_name', '').strip()
        child_last_name = request.POST.get('child_last_name', '').strip()
        date_of_birth = request.POST.get('date_of_birth', '').strip()
        sex = request.POST.get('sex', '').strip()

        if not child_over_18:
            messages.error(request, 'Please indicate whether the child is over 18 years of age.')
            return redirect('ecitizen_child_details')

        if not born_in_health_facility:
            messages.error(request, 'Please indicate whether the child was born in a health facility.')
            return redirect('ecitizen_child_details')

        if not county_of_birth:
            messages.error(request, 'Please select the county of birth.')
            return redirect('ecitizen_child_details')

        if not notification_number:
            messages.error(request, 'Please enter the entry or notification number.')
            return redirect('ecitizen_child_details')

        if not child_first_name:
            messages.error(request, 'Please enter the child first name.')
            return redirect('ecitizen_child_details')

        application.child_over_18 = child_over_18
        application.born_in_health_facility = born_in_health_facility
        application.county_of_birth = county_of_birth
        application.notification_number = notification_number
        application.child_first_name = child_first_name
        application.child_middle_name = child_middle_name
        application.child_last_name = child_last_name
        application.date_of_birth = date_of_birth or None
        application.sex = sex or None
        application.save()

        return redirect('ecitizen_parents_information')

    context = {
        'application': application,
    }
    return render(request, 'queueing/ecitizen_child_details.html', context)


@login_required
def ecitizen_parents_information(request):
    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'Only applicants can access the eCitizen simulation.')
        return redirect('login')

    if not request.session.get('ecitizen_verified'):
        messages.error(request, 'Please log in through the eCitizen simulation first.')
        return redirect('ecitizen_login')

    applicant = request.user.applicant_profile
    application = get_or_create_draft_application(applicant)

    if request.method == 'POST':
        father_full_name = request.POST.get('father_full_name', '').strip()
        father_id_number = request.POST.get('father_id_number', '').strip()
        mother_full_name = request.POST.get('mother_full_name', '').strip()
        mother_id_number = request.POST.get('mother_id_number', '').strip()
        parent_phone_number = request.POST.get('parent_phone_number', '').strip()

        if not father_full_name:
            messages.error(request, 'Please enter the father full name.')
            return redirect('ecitizen_parents_information')

        if not mother_full_name:
            messages.error(request, 'Please enter the mother full name.')
            return redirect('ecitizen_parents_information')

        if not parent_phone_number:
            messages.error(request, 'Please enter the parent phone number.')
            return redirect('ecitizen_parents_information')

        application.father_full_name = father_full_name
        application.father_id_number = father_id_number
        application.mother_full_name = mother_full_name
        application.mother_id_number = mother_id_number
        application.parent_phone_number = parent_phone_number
        application.save()

        return redirect('ecitizen_uploads')

    context = {
        'application': application,
    }
    return render(request, 'queueing/ecitizen_parents_information.html', context)


@login_required
def ecitizen_uploads(request):
    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'Only applicants can access the eCitizen simulation.')
        return redirect('login')

    if not request.session.get('ecitizen_verified'):
        messages.error(request, 'Please log in through the eCitizen simulation first.')
        return redirect('ecitizen_login')

    applicant = request.user.applicant_profile
    application = get_or_create_draft_application(applicant)

    if request.method == 'POST':
        birth_notification = request.FILES.get('upload_birth_notification')
        applicant_id_file = request.FILES.get('upload_applicant_id')
        parent_id_file = request.FILES.get('upload_parent_id')

        if not birth_notification:
            messages.error(request, 'Please upload the birth notification document.')
            return redirect('ecitizen_uploads')

        if not parent_id_file:
            messages.error(request, 'Please upload the parent identification document.')
            return redirect('ecitizen_uploads')

        application.upload_birth_notification = birth_notification
        application.upload_applicant_id = applicant_id_file
        application.upload_parent_id = parent_id_file
        application.save()

        return redirect('ecitizen_review_payment')

    context = {
        'application': application,
    }
    return render(request, 'queueing/ecitizen_uploads.html', context)


@login_required
def ecitizen_review_payment(request):
    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'Only applicants can access the eCitizen simulation.')
        return redirect('login')

    if not request.session.get('ecitizen_verified'):
        messages.error(request, 'Please log in through the eCitizen simulation first.')
        return redirect('ecitizen_login')

    applicant = request.user.applicant_profile
    application = get_or_create_draft_application(applicant)

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method', '').strip()
        payment_phone = request.POST.get('payment_phone', '').strip()
        airtel_phone = request.POST.get('airtel_phone', '').strip()
        card_name = request.POST.get('card_name', '').strip()
        card_number = request.POST.get('card_number', '').strip()
        expiry_date = request.POST.get('expiry_date', '').strip()
        cvv = request.POST.get('cvv', '').strip()

        if not payment_method:
            messages.error(request, 'Please select a payment method.')
            return redirect('ecitizen_review_payment')

        if payment_method == 'M-Pesa':
            if not payment_phone:
                messages.error(request, 'Please enter the M-Pesa number.')
                return redirect('ecitizen_review_payment')

        elif payment_method == 'Airtel Money':
            if not airtel_phone:
                messages.error(request, 'Please enter the Airtel number.')
                return redirect('ecitizen_review_payment')

        elif payment_method == 'Card':
            if not all([card_name, card_number, expiry_date, cvv]):
                messages.error(request, 'Please complete all card details.')
                return redirect('ecitizen_review_payment')

        application.ecitizen_application_ref = generate_ecitizen_reference()
        application.processing_status = 'submitted'
        application.document_status = 'complete'
        application.save()

        auto_transaction_code = f"TXN2026{application.id:05d}"

        request.session['latest_invoice_number'] = generate_invoice_number()
        request.session['latest_receipt_number'] = generate_receipt_number()
        request.session['latest_payment_method'] = payment_method
        request.session['latest_transaction_code'] = auto_transaction_code

        if payment_method == 'M-Pesa':
            request.session['latest_payment_phone'] = payment_phone
        elif payment_method == 'Airtel Money':
            request.session['latest_payment_phone'] = airtel_phone
        else:
            request.session['latest_payment_phone'] = 'Card Payment'

        messages.success(
            request,
            f'Payment successful. Your eCitizen reference is {application.ecitizen_application_ref}.'
        )
        return redirect('ecitizen_application_success', application_id=application.id)

    context = {
        'application': application,
        'amount_without_amendment': 200,
        'amount_with_amendment': 1000,
        'ecitizen_access_fee': 50,
    }
    return render(request, 'queueing/ecitizen_review_payment.html', context)
    
@login_required
def ecitizen_application_success(request, application_id):
    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'Only applicants can access this page.')
        return redirect('login')

    applicant = request.user.applicant_profile
    application = get_object_or_404(Application, id=application_id, applicant=applicant)

    context = {
        'application': application,
        'invoice_number': request.session.get('latest_invoice_number', 'N/A'),
        'receipt_number': request.session.get('latest_receipt_number', 'N/A'),
        'payment_method': request.session.get('latest_payment_method', 'N/A'),
        'transaction_code': request.session.get('latest_transaction_code', 'N/A'),
        'payment_phone': request.session.get('latest_payment_phone', 'N/A'),
    }
    return render(request, 'queueing/ecitizen_application_success.html', context)


@login_required
def huduma_login_view(request):
    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'Only applicants can access the Huduma appointment simulation.')
        return redirect('login')

    applicant = request.user.applicant_profile

    if request.method == 'POST':
        national_id = request.POST.get('national_id', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        mother_first_name = request.POST.get('mother_first_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()

        if national_id != applicant.national_id:
            messages.error(request, 'National ID does not match the logged-in applicant.')
            return redirect('huduma_login')

        if first_name == '':
            messages.error(request, 'First name is required for this simulation.')
            return redirect('huduma_login')

        if mother_first_name == '':
            messages.error(request, 'Mother’s first name is required for this simulation.')
            return redirect('huduma_login')

        request.session['huduma_verified'] = True
        request.session['huduma_identity'] = {
            'national_id': national_id,
            'first_name': first_name,
            'mother_first_name': mother_first_name,
            'phone': phone,
            'email': email,
        }

        messages.success(request, 'Huduma appointment verification successful.')
        return redirect('huduma_booking_create')

    context = {
        'applicant': applicant,
    }
    return render(request, 'queueing/huduma_login.html', context)


@login_required
def huduma_booking_create(request):
    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'Only applicants can access the Huduma appointment simulation.')
        return redirect('login')

    if not request.session.get('huduma_verified'):
        messages.error(request, 'Please complete Huduma verification first.')
        return redirect('huduma_login')

    applicant = request.user.applicant_profile
    latest_application = (
        Application.objects.filter(
            applicant=applicant,
            service_category__name='birth_certificate',
            processing_status='submitted'
        )
        .order_by('-id')
        .first()
    )

    if not latest_application:
        messages.error(request, 'You must complete the eCitizen application stage first.')
        return redirect('ecitizen_login')

    if request.method == 'POST':
        appointment_date = request.POST.get('appointment_date')
        appointment_time = request.POST.get('appointment_time')

        if not appointment_date or not appointment_time:
            messages.error(request, 'Please select appointment date and time.')
            return redirect('huduma_booking_create')

        booking_reference = generate_huduma_booking_reference()

        appointment = Appointment.objects.create(
            applicant=applicant,
            service_category=latest_application.service_category,
            huduma_booking_ref=booking_reference,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            booking_status='booked',
        )

        QueueTicket.objects.create(
            applicant=applicant,
            application=latest_application,
            appointment=appointment,
            ticket_number=generate_ticket_number(),
            current_status='tracking',
            arrival_confirmed=False,
            estimated_wait_minutes=0,
        )

        request.session['latest_huduma_booking_reference'] = booking_reference
        request.session['linked_application_reference'] = latest_application.ecitizen_application_ref

        messages.success(
            request,
            f'Appointment booked successfully. Your booking reference is {booking_reference}.'
        )
        return redirect('huduma_booking_success', appointment_id=appointment.id)

    context = {
        'applicant': applicant,
        'application': latest_application,
    }
    return render(request, 'queueing/huduma_booking_form.html', context)


@login_required
def huduma_booking_success(request, appointment_id):
    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'Only applicants can access this page.')
        return redirect('login')

    applicant = request.user.applicant_profile
    appointment = get_object_or_404(Appointment, id=appointment_id, applicant=applicant)

    context = {
        'appointment': appointment,
        'application_reference': request.session.get('linked_application_reference', 'N/A'),
    }
    return render(request, 'queueing/huduma_booking_success.html', context)

@login_required
def applicant_notifications(request):
    if not hasattr(request.user, 'applicant_profile'):
        return JsonResponse({'error': 'Applicant profile not found.'}, status=403)

    applicant = request.user.applicant_profile

    notifications = Notification.objects.filter(applicant=applicant)[:20]
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
        return JsonResponse({'error': 'Applicant profile not found.'}, status=403)

    applicant = request.user.applicant_profile

    Notification.objects.filter(
        applicant=applicant,
        is_read=False
    ).update(is_read=True)

    return JsonResponse({'success': True})