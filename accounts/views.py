from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages

from .models import ApplicantProfile
from queueing.models import Application, Appointment, ServiceOfficer


def get_next_applicant_route(user):
    if not hasattr(user, 'applicant_profile'):
        return 'login'

    applicant = user.applicant_profile

    application = Application.objects.filter(applicant=applicant).order_by('-submitted_at').first()
    appointment = Appointment.objects.filter(applicant=applicant).order_by('-appointment_date', '-appointment_time').first()

    if not application:
        return 'ecitizen_login'

    if not application.ecitizen_application_ref:
        return 'ecitizen_login'

    if not appointment:
        return 'huduma_login'

    return 'applicant_dashboard'


def applicant_register(request):
    if request.method == 'POST':
        full_name = request.POST.get('full_name', '').strip()
        national_id = request.POST.get('national_id', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        email = request.POST.get('email', '').strip()
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        if not all([full_name, national_id, phone_number, email, username, password, confirm_password]):
            messages.error(request, 'All fields are required.')
            return redirect('applicant_register')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('applicant_register')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('applicant_register')

        if ApplicantProfile.objects.filter(national_id=national_id).exists():
            messages.error(request, 'National ID already exists.')
            return redirect('applicant_register')

        if ApplicantProfile.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('applicant_register')

        name_parts = full_name.split()
        first_name = name_parts[0] if name_parts else ''
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )

        ApplicantProfile.objects.create(
            user=user,
            full_name=full_name,
            national_id=national_id,
            phone_number=phone_number,
            email=email,
        )

        login(request, user)
        messages.success(request, 'Account created successfully.')
        return redirect('ecitizen_login')

    return render(request, 'accounts/register.html')


def login_view(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'applicant_profile'):
            return redirect(get_next_applicant_route(request.user))

        if ServiceOfficer.objects.filter(user=request.user).exists():
            return redirect('staff_dashboard')

        logout(request)
        messages.error(request, 'This account is not registered as an applicant or staff account.')
        return redirect('login')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if hasattr(user, 'applicant_profile'):
                login(request, user)
                return redirect(get_next_applicant_route(user))

            if ServiceOfficer.objects.filter(user=user).exists():
                messages.error(request, 'Use staff login.')
                return redirect('staff_login')

            messages.error(request, 'This account is not registered as an applicant or staff account.')
            return redirect('login')

        messages.error(request, 'Invalid username or password.')

    return render(request, 'accounts/login.html')


def staff_login_view(request):
    if request.user.is_authenticated:
        if ServiceOfficer.objects.filter(user=request.user).exists():
            return redirect('staff_dashboard')

        if hasattr(request.user, 'applicant_profile'):
            return redirect(get_next_applicant_route(request.user))

        logout(request)
        messages.error(request, 'This account is not registered as a staff account.')
        return redirect('staff_login')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if hasattr(user, 'applicant_profile'):
                messages.error(request, 'Applicants must use applicant login.')
                return redirect('login')

            if not ServiceOfficer.objects.filter(user=user).exists():
                messages.error(request, 'This account is not registered as a staff account.')
                return redirect('staff_login')

            login(request, user)
            return redirect('staff_dashboard')

        messages.error(request, 'Invalid username or password.')

    return render(request, 'accounts/staff_login.html')


def logout_view(request):
    logout(request)
    return redirect('login')