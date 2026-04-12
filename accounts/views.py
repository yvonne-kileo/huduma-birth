from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import ApplicantProfile
from queueing.models import Application, Appointment


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
            messages.error(request, 'An applicant with this National ID already exists.')
            return redirect('applicant_register')

        if ApplicantProfile.objects.filter(email=email).exists():
            messages.error(request, 'An applicant with this email already exists.')
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

        messages.success(request, 'Registration successful. You can now log in.')
        return redirect('login')

    return render(request, 'accounts/register.html')


def get_applicant_next_step(user):
    applicant = user.applicant_profile

    has_application = Application.objects.filter(applicant=applicant).exists()
    has_appointment = Appointment.objects.filter(applicant=applicant).exists()

    if not has_application:
        return 'ecitizen_login'
    elif has_application and not has_appointment:
        return 'huduma_login'
    else:
        return 'applicant_dashboard'


def login_view(request):
    if request.user.is_authenticated:
        if hasattr(request.user, 'service_officer_profile'):
            return redirect('staff_dashboard')
        elif hasattr(request.user, 'applicant_profile'):
            return redirect(get_applicant_next_step(request.user))
        else:
            return redirect('admin:index')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if hasattr(user, 'service_officer_profile'):
                return redirect('staff_dashboard')
            elif hasattr(user, 'applicant_profile'):
                return redirect(get_applicant_next_step(user))
            else:
                return redirect('admin:index')
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')