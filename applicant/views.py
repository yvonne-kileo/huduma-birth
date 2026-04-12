from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse

from queueing.models import Appointment, Application, QueueTicket, QueueStatusHistory


def generate_ticket_number():
    latest_ticket = QueueTicket.objects.order_by('-id').first()
    next_id = 1 if latest_ticket is None else latest_ticket.id + 1
    return f"TKT{next_id:04d}"


@login_required
def applicant_dashboard(request):
    if not hasattr(request.user, 'applicant_profile'):
        messages.error(request, 'You do not have applicant access.')
        return redirect('login')

    applicant = request.user.applicant_profile

    appointment = Appointment.objects.filter(applicant=applicant).order_by('-id').first()
    application = Application.objects.filter(applicant=applicant).order_by('-id').first()

    queue_ticket = None

    # Auto-create queue ticket if both appointment and application exist
    if appointment and application:
        queue_ticket, created = QueueTicket.objects.get_or_create(
            appointment=appointment,
            defaults={
                'application': application,
                'applicant': applicant,
                'ticket_number': generate_ticket_number(),
                'current_status': 'tracking',
                'arrival_confirmed': False,
                'estimated_wait_minutes': 15,
            }
        )

        if not created:
            updated = False

            if queue_ticket.applicant_id != applicant.id:
                queue_ticket.applicant = applicant
                updated = True

            if queue_ticket.application_id != application.id:
                queue_ticket.application = application
                updated = True

            if updated:
                queue_ticket.save()

    verification_status = False
    if application and appointment and queue_ticket:
        verification_status = True

    context = {
        'applicant': applicant,
        'appointment': appointment,
        'application': application,
        'queue_ticket': queue_ticket,
        'verification_status': verification_status,
        'is_applicant': True,
        'is_staff_user': False,
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
        messages.info(request, 'Arrival has already been confirmed.')
        return redirect('applicant_dashboard')

    ticket.arrival_confirmed = True
    ticket.current_status = 'waiting'
    ticket.joined_queue_at = timezone.now()
    ticket.save()

    QueueStatusHistory.objects.create(
        queue_ticket=ticket,
        updated_by=None,
        status='waiting',
        notes='Applicant confirmed arrival at the centre.'
    )

    messages.success(request, 'Arrival confirmed successfully. Your ticket status is now WAITING.')
    return redirect('applicant_dashboard')


@login_required
def applicant_queue_status(request):
    if not hasattr(request.user, 'applicant_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    applicant = request.user.applicant_profile
    queue_ticket = QueueTicket.objects.filter(applicant=applicant).order_by('-id').first()

    if not queue_ticket:
        return JsonResponse({'error': 'No queue ticket found'}, status=404)

    waiting_tickets = list(
        QueueTicket.objects.filter(current_status='waiting')
        .order_by('joined_queue_at')
    )

    position = None
    people_ahead = 0
    queue_list = []

    if queue_ticket.current_status == 'waiting':
        for index, ticket in enumerate(waiting_tickets):
            queue_list.append({
                'id': ticket.id,
                'ticket_number': ticket.ticket_number,
                'is_me': ticket.id == queue_ticket.id
            })

            if ticket.id == queue_ticket.id:
                position = index + 1
                people_ahead = index

    data = {
        'ticket_number': queue_ticket.ticket_number,
        'current_status': queue_ticket.current_status,
        'current_status_display': queue_ticket.get_current_status_display(),
        'arrival_confirmed': queue_ticket.arrival_confirmed,
        'estimated_wait_minutes': queue_ticket.estimated_wait_minutes,
        'position': position,
        'people_ahead': people_ahead,
        'queue_total': len(waiting_tickets),
        'queue_list': queue_list,
        'large_queue_mode': len(waiting_tickets) > 10,
    }

    return JsonResponse(data)