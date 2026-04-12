from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.db.models import Avg

from queueing.models import Application, Appointment, QueueTicket


@login_required
def reports_dashboard(request):
    if not hasattr(request.user, 'service_officer_profile'):
        return redirect('login')

    total_applications = Application.objects.count()
    total_appointments = Appointment.objects.count()
    total_tickets = QueueTicket.objects.count()

    waiting_tickets = QueueTicket.objects.filter(current_status='waiting').count()
    called_tickets = QueueTicket.objects.filter(current_status='called').count()
    in_service_tickets = QueueTicket.objects.filter(current_status='in_service').count()
    completed_tickets = QueueTicket.objects.filter(current_status='completed').count()
    tracking_tickets = QueueTicket.objects.filter(current_status='tracking').count()

    avg_wait = QueueTicket.objects.aggregate(avg_wait=Avg('estimated_wait_minutes'))['avg_wait'] or 0
    avg_wait = round(avg_wait, 1)

    recent_tickets = (
        QueueTicket.objects.select_related('applicant', 'appointment')
        .order_by('-id')[:10]
    )

    hour_buckets = {
        '08:00': 0,
        '09:00': 0,
        '10:00': 0,
        '11:00': 0,
        '12:00': 0,
        '14:00': 0,
        '15:00': 0,
        '16:00': 0,
    }

    appointments = Appointment.objects.all()
    for appointment in appointments:
        if appointment.appointment_time:
            hour_key = appointment.appointment_time.strftime('%H:%M')
            if hour_key in hour_buckets:
                hour_buckets[hour_key] += 1

    max_bucket_value = max(hour_buckets.values()) if hour_buckets else 1
    if max_bucket_value == 0:
        max_bucket_value = 1

    peak_hour_data = []
    for hour, count in hour_buckets.items():
        percentage = (count / max_bucket_value) * 100
        peak_hour_data.append({
            'hour': hour,
            'count': count,
            'percentage': round(percentage, 1),
        })

    busiest_slot = max(hour_buckets, key=hour_buckets.get) if hour_buckets else 'N/A'
    busiest_slot_count = hour_buckets[busiest_slot] if busiest_slot != 'N/A' else 0

    context = {
        'total_applications': total_applications,
        'total_appointments': total_appointments,
        'total_tickets': total_tickets,
        'waiting_tickets': waiting_tickets,
        'called_tickets': called_tickets,
        'in_service_tickets': in_service_tickets,
        'completed_tickets': completed_tickets,
        'tracking_tickets': tracking_tickets,
        'avg_wait': avg_wait,
        'recent_tickets': recent_tickets,
        'peak_hour_data': peak_hour_data,
        'busiest_slot': busiest_slot,
        'busiest_slot_count': busiest_slot_count,
        'is_applicant': False,
        'is_staff_user': True,
    }

    return render(request, 'reports/reports_dashboard.html', context)