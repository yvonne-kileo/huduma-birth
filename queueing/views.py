from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Max

from .models import ServiceCategory, Application
from datetime import datetime
from .models import Appointment


def generate_ecitizen_reference():
    latest_application = Application.objects.aggregate(max_id=Max('id'))
    next_id = (latest_application['max_id'] or 0) + 1
    return f"ECIT2026{next_id:04d}"


def generate_invoice_number():
    latest_application = Application.objects.aggregate(max_id=Max('id'))
    next_id = (latest_application['max_id'] or 0) + 1
    return f"INV2026{next_id:04d}"


@login_required
def ecitizen_login_view(request):
    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'Only applicants can access the eCitizen simulation.')
        return redirect('login')

    applicant = request.user.applicant_profile

    if request.method == 'POST':
        national_id = request.POST.get('national_id')
        password = request.POST.get('password')

        if national_id != applicant.national_id:
            messages.error(request, 'National ID does not match the logged-in applicant.')
            return redirect('ecitizen_login')

        if password != 'ecitizen123':
            messages.error(request, 'Invalid eCitizen password.')
            return redirect('ecitizen_login')

        request.session['ecitizen_verified'] = True
        messages.success(request, 'eCitizen login successful.')
        return redirect('crs_service_selection')

    context = {
        'applicant': applicant,
    }
    return render(request, 'queueing/ecitizen_login.html', context)


@login_required
def crs_service_selection(request):
    if not request.session.get('ecitizen_verified'):
        messages.error(request, 'Please log in through the eCitizen simulation first.')
        return redirect('ecitizen_login')

    return render(request, 'queueing/crs_service_selection.html')


@login_required
def ecitizen_application_create(request):
    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'Only applicants can access the eCitizen simulation.')
        return redirect('login')

    if not request.session.get('ecitizen_verified'):
        messages.error(request, 'Please log in through the eCitizen simulation first.')
        return redirect('ecitizen_login')

    applicant = request.user.applicant_profile
    service_categories = ServiceCategory.objects.all()

    if request.method == 'POST':
        service_category_id = request.POST.get('service_category')
        birth_notification_number = request.POST.get('birth_notification_number')
        father_name = request.POST.get('father_name')
        mother_name = request.POST.get('mother_name')

        if not service_category_id:
            messages.error(request, 'Please select a service category.')
            return redirect('ecitizen_application_create')

        try:
            service_category = ServiceCategory.objects.get(id=service_category_id)
        except ServiceCategory.DoesNotExist:
            messages.error(request, 'Selected service category does not exist.')
            return redirect('ecitizen_application_create')

        request.session['pending_ecitizen_application'] = {
            'service_category_id': service_category.id,
            'birth_notification_number': birth_notification_number,
            'father_name': father_name,
            'mother_name': mother_name,
            'invoice_number': generate_invoice_number(),
            'amount': 150,
        }

        return redirect('ecitizen_payment')

    context = {
        'applicant': applicant,
        'service_categories': service_categories,
    }
    return render(request, 'queueing/ecitizen_application_form.html', context)


@login_required
def ecitizen_payment(request):
    if not request.session.get('ecitizen_verified'):
        messages.error(request, 'Please log in through the eCitizen simulation first.')
        return redirect('ecitizen_login')

    pending = request.session.get('pending_ecitizen_application')
    if not pending:
        messages.error(request, 'No pending application found.')
        return redirect('ecitizen_application_create')

    if request.method == 'POST':
        if not hasattr(request.user, 'applicant_profile'):
            messages.error(request, 'Only applicants can access this page.')
            return redirect('login')

        applicant = request.user.applicant_profile
        service_category = ServiceCategory.objects.get(id=pending['service_category_id'])

        payment_method = request.POST.get('payment_method')
        transaction_code = request.POST.get('transaction_code')
        payment_phone = request.POST.get('payment_phone')

        if not payment_method:
            messages.error(request, 'Please select a payment method.')
            return redirect('ecitizen_payment')

        if not transaction_code:
            messages.error(request, 'Please enter a transaction code.')
            return redirect('ecitizen_payment')

        application_reference = generate_ecitizen_reference()
        receipt_number = f"RCT2026{application_reference[-4:]}"

        application = Application.objects.create(
            applicant=applicant,
            service_category=service_category,
            ecitizen_application_ref=application_reference,
            document_status='pending',
            processing_status='not_started',
        )

        request.session['latest_invoice_number'] = pending['invoice_number']
        request.session['latest_receipt_number'] = receipt_number
        request.session['latest_payment_method'] = payment_method
        request.session['latest_transaction_code'] = transaction_code
        request.session['latest_payment_phone'] = payment_phone or 'N/A'

        del request.session['pending_ecitizen_application']

        messages.success(
            request,
            f'Payment successful. Your eCitizen reference is {application.ecitizen_application_ref}.'
        )
        return redirect('ecitizen_application_success', application_id=application.id)

    context = {
        'pending': pending,
    }
    return render(request, 'queueing/ecitizen_payment.html', context)

@login_required
def ecitizen_application_success(request, application_id):
    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'Only applicants can access this page.')
        return redirect('login')

    applicant = request.user.applicant_profile

    try:
        application = Application.objects.get(id=application_id, applicant=applicant)
    except Application.DoesNotExist:
        messages.error(request, 'Application not found.')
        return redirect('applicant_dashboard')

    context = {
        'application': application,
        'invoice_number': request.session.get('latest_invoice_number', 'N/A'),
        'receipt_number': request.session.get('latest_receipt_number', 'N/A'),
        'payment_method': request.session.get('latest_payment_method', 'N/A'),
        'transaction_code': request.session.get('latest_transaction_code', 'N/A'),
        'payment_phone': request.session.get('latest_payment_phone', 'N/A'),
    }

    return render(request, 'queueing/ecitizen_application_success.html', context)

def generate_huduma_booking_reference():
    latest_appointment = Appointment.objects.aggregate(max_id=Max('id'))
    next_id = (latest_appointment['max_id'] or 0) + 1
    return f"HUD2026{next_id:04d}"


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

        print("DEBUG mother_first_name =", mother_first_name)

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
    latest_application = Application.objects.filter(applicant=applicant).order_by('-id').first()

    if not latest_application:
        messages.error(request, 'You must complete the eCitizen application stage first.')
        return redirect('ecitizen_login')

    if request.method == 'POST':
        appointment_date = request.POST.get('appointment_date')
        appointment_time = request.POST.get('appointment_time')

        if not appointment_date or not appointment_time:
            messages.error(request, 'Please select appointment date and time.')
            return redirect('huduma_booking_create')

        service_category = latest_application.service_category
        booking_reference = generate_huduma_booking_reference()

        appointment = Appointment.objects.create(
            applicant=applicant,
            service_category=service_category,
            huduma_booking_ref=booking_reference,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            booking_status='booked',
        )

        request.session['latest_huduma_booking_reference'] = booking_reference
        request.session['linked_application_reference'] = latest_application.ecitizen_application_ref

        messages.success(request, f'Appointment booked successfully. Your booking reference is {booking_reference}.')
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

    try:
        appointment = Appointment.objects.get(id=appointment_id, applicant=applicant)
    except Appointment.DoesNotExist:
        messages.error(request, 'Appointment not found.')
        return redirect('applicant_dashboard')

    context = {
        'appointment': appointment,
        'application_reference': request.session.get('linked_application_reference', 'N/A'),
    }
    return render(request, 'queueing/huduma_booking_success.html', context)