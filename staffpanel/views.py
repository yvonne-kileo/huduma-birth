from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from queueing.models import QueueTicket, QueueStatusHistory
from accounts.models import ServiceOfficer
from django.http import JsonResponse


@login_required
def staff_dashboard(request):
    if not hasattr(request.user, 'service_officer_profile'):
        messages.error(request, 'You do not have staff access.')
        return redirect('login')

    officer = request.user.service_officer_profile

    waiting_tickets = QueueTicket.objects.filter(current_status='waiting').order_by('joined_queue_at')
    called_tickets = QueueTicket.objects.filter(current_status='called')
    in_service_tickets = QueueTicket.objects.filter(current_status='in_service')

    context = {
        'officer': officer,
        'waiting_tickets': waiting_tickets,
        'called_tickets': called_tickets,
        'in_service_tickets': in_service_tickets,
        'is_applicant': False,
        'is_staff_user': True,
    }

    return render(request, 'staffpanel/dashboard.html', context)


@login_required
def call_next(request, ticket_id):
    if not hasattr(request.user, 'service_officer_profile'):
        return redirect('login')

    officer = request.user.service_officer_profile
    ticket = get_object_or_404(QueueTicket, id=ticket_id)

    ticket.current_status = 'called'
    ticket.save()

    QueueStatusHistory.objects.create(
        queue_ticket=ticket,
        updated_by=officer,
        status='called',
        notes='Applicant called to counter.'
    )

    messages.success(request, f'Ticket {ticket.ticket_number} called.')
    return redirect('staff_dashboard')


@login_required
def start_service(request, ticket_id):
    officer = request.user.service_officer_profile
    ticket = get_object_or_404(QueueTicket, id=ticket_id)

    ticket.current_status = 'in_service'
    ticket.save()

    QueueStatusHistory.objects.create(
        queue_ticket=ticket,
        updated_by=officer,
        status='in_service',
        notes='Service started.'
    )

    return redirect('staff_dashboard')


@login_required
def complete_service(request, ticket_id):
    officer = request.user.service_officer_profile
    ticket = get_object_or_404(QueueTicket, id=ticket_id)

    ticket.current_status = 'completed'
    ticket.save()

    QueueStatusHistory.objects.create(
        queue_ticket=ticket,
        updated_by=officer,
        status='completed',
        notes='Service completed.'
    )

    return redirect('staff_dashboard')

@login_required
def staff_queue_data(request):
    if not hasattr(request.user, 'service_officer_profile'):
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    waiting_tickets = list(
        QueueTicket.objects.filter(current_status='waiting')
        .order_by('joined_queue_at')
        .values('id', 'ticket_number', 'applicant__full_name')
    )

    called_tickets = list(
        QueueTicket.objects.filter(current_status='called')
        .values('id', 'ticket_number', 'applicant__full_name')
    )

    in_service_tickets = list(
        QueueTicket.objects.filter(current_status='in_service')
        .values('id', 'ticket_number', 'applicant__full_name')
    )

    return JsonResponse({
        'waiting_tickets': waiting_tickets,
        'called_tickets': called_tickets,
        'in_service_tickets': in_service_tickets,
    })