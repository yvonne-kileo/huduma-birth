from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from queueing.models import Application, QueueTicket, QueueStatusHistory, Notification


def create_notification(
    applicant,
    title,
    message,
    notification_type='system',
    link='',
    metadata_key=''
):
    """
    Creates or updates an applicant notification.

    metadata_key prevents duplicate notifications.
    Example:
    queue-position-5 will keep updating the same queue position notification
    instead of creating many repeated messages.
    """

    if not applicant:
        return None

    if metadata_key:
        notification, created = Notification.objects.update_or_create(
            applicant=applicant,
            metadata_key=metadata_key,
            defaults={
                'title': title,
                'message': message,
                'notification_type': notification_type,
                'link': link,
                'is_read': False,
            }
        )
        return notification

    return Notification.objects.create(
        applicant=applicant,
        title=title,
        message=message,
        notification_type=notification_type,
        link=link,
        metadata_key=metadata_key
    )


def get_applicant_dashboard_link():
    try:
        return reverse('applicant_dashboard')
    except Exception:
        return ''


def build_queue_update_data(ticket):
    waiting_tickets = list(
        QueueTicket.objects.filter(current_status='waiting')
        .order_by('joined_queue_at')
    )

    position = None
    people_ahead = 0
    queue_list = []

    if ticket.current_status == 'waiting':
        for index, item in enumerate(waiting_tickets):
            queue_list.append({
                'id': item.id,
                'ticket_number': item.ticket_number,
                'is_me': item.id == ticket.id,
            })

            if item.id == ticket.id:
                position = index + 1
                people_ahead = index

    data = {
        'ticket_number': ticket.ticket_number,
        'current_status': ticket.current_status,
        'current_status_display': ticket.get_current_status_display(),
        'arrival_confirmed': ticket.arrival_confirmed,
        'estimated_wait_minutes': ticket.estimated_wait_minutes,
        'position': position,
        'people_ahead': people_ahead,
        'queue_total': len(waiting_tickets),
        'queue_list': queue_list,
        'large_queue_mode': len(waiting_tickets) > 10,
    }

    return data


def push_queue_update(ticket):
    channel_layer = get_channel_layer()

    data = build_queue_update_data(ticket)

    if ticket.current_status == 'waiting' and data['position']:
        create_notification(
            applicant=ticket.applicant,
            title='Queue position updated',
            message=(
                f'Your queue position is {data["position"]}. '
                f'Estimated waiting time is {ticket.estimated_wait_minutes} minutes.'
            ),
            notification_type='queue',
            link=get_applicant_dashboard_link(),
            metadata_key=f'queue-position-{ticket.id}'
        )

    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            f'queue_applicant_{ticket.applicant.id}',
            {
                'type': 'queue_update',
                'data': data,
            }
        )


def push_waiting_queue_updates():
    waiting_tickets = QueueTicket.objects.filter(
        current_status='waiting'
    ).order_by('joined_queue_at')

    for ticket in waiting_tickets:
        push_queue_update(ticket)


def notify_application_status(application):
    applicant = application.applicant
    dashboard_link = get_applicant_dashboard_link()

    processing_status = application.processing_status
    document_status = application.document_status

    collection_date = getattr(application, 'collection_date', None)

    if collection_date and processing_status in ['approved', 'ready_for_collection']:
        create_notification(
            applicant=applicant,
            title='Document ready for collection',
            message=f'Your birth certificate will be ready for collection on {collection_date}.',
            notification_type='collection',
            link=dashboard_link,
            metadata_key=f'collection-ready-{application.id}'
        )
        return

    if processing_status == 'under_review' and document_status == 'incomplete':
        create_notification(
            applicant=applicant,
            title='Application incomplete',
            message='Your birth certificate application is incomplete. Please check the review notes for correction instructions.',
            notification_type='application',
            link=dashboard_link,
            metadata_key=f'application-incomplete-{application.id}'
        )
        return

    if processing_status == 'under_review':
        create_notification(
            applicant=applicant,
            title='Application under review',
            message='Your birth certificate application is now under review by the service officer.',
            notification_type='application',
            link=dashboard_link,
            metadata_key=f'application-under-review-{application.id}'
        )
        return

    if processing_status == 'approved' and document_status == 'verified':
        create_notification(
            applicant=applicant,
            title='Application verified',
            message='Your birth certificate application and supporting documents have been verified. You will be notified when the certificate is ready for collection.',
            notification_type='application',
            link=dashboard_link,
            metadata_key=f'application-approved-{application.id}'
        )
        return

    if processing_status == 'rejected':
        create_notification(
            applicant=applicant,
            title='Application rejected',
            message='Your birth certificate application was rejected during review. Please check the review notes for details.',
            notification_type='application',
            link=dashboard_link,
            metadata_key=f'application-rejected-{application.id}'
        )
        return

    create_notification(
        applicant=applicant,
        title='Application status updated',
        message=f'Your application status has been updated to {processing_status}.',
        notification_type='application',
        link=dashboard_link,
        metadata_key=f'application-status-{application.id}-{processing_status}-{document_status}'
    )


@login_required
def staff_dashboard(request):
    if not hasattr(request.user, 'service_officer_profile'):
        messages.error(request, 'You do not have staff access.')
        return redirect('login')

    officer = request.user.service_officer_profile

    waiting_tickets = QueueTicket.objects.filter(
        current_status='waiting'
    ).order_by('joined_queue_at')

    called_tickets = QueueTicket.objects.filter(
        current_status='called'
    )

    in_service_tickets = QueueTicket.objects.filter(
        current_status='in_service'
    )

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
        messages.error(request, 'You do not have staff access.')
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

    create_notification(
        applicant=ticket.applicant,
        title='You have been called',
        message=f'Your ticket {ticket.ticket_number} has been called. Please proceed to the service counter.',
        notification_type='queue',
        link=get_applicant_dashboard_link(),
        metadata_key=f'queue-called-{ticket.id}'
    )

    push_queue_update(ticket)

    # After one applicant is called, the remaining waiting applicants move forward.
    push_waiting_queue_updates()

    messages.success(request, f'Ticket {ticket.ticket_number} called.')
    return redirect('staff_dashboard')


@login_required
def start_service(request, ticket_id):
    if not hasattr(request.user, 'service_officer_profile'):
        messages.error(request, 'You do not have staff access.')
        return redirect('login')

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

    create_notification(
        applicant=ticket.applicant,
        title='Service started',
        message=f'Your ticket {ticket.ticket_number} is now being served.',
        notification_type='queue',
        link=get_applicant_dashboard_link(),
        metadata_key=f'queue-service-started-{ticket.id}'
    )

    push_queue_update(ticket)

    return redirect('staff_dashboard')


@login_required
def complete_service(request, ticket_id):
    if not hasattr(request.user, 'service_officer_profile'):
        messages.error(request, 'You do not have staff access.')
        return redirect('login')

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

    create_notification(
        applicant=ticket.applicant,
        title='Counter service completed',
        message=f'Your counter service for ticket {ticket.ticket_number} has been completed.',
        notification_type='queue',
        link=get_applicant_dashboard_link(),
        metadata_key=f'queue-service-completed-{ticket.id}'
    )

    push_queue_update(ticket)

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


@login_required
def application_review_list(request):
    if not hasattr(request.user, 'service_officer_profile'):
        messages.error(request, 'You do not have staff access.')
        return redirect('login')

    applications = Application.objects.select_related(
        'applicant',
        'service_category'
    ).order_by('-submitted_at')

    context = {
        'applications': applications,
    }

    return render(request, 'staffpanel/application_review_list.html', context)


@login_required
def application_review_action(request, application_id, action):
    if not hasattr(request.user, 'service_officer_profile'):
        messages.error(request, 'You do not have staff access.')
        return redirect('login')

    application = get_object_or_404(Application, id=application_id)

    if action == 'under_review':
        application.processing_status = 'under_review'
        application.review_notes = 'Application moved to review stage.'
        application.save()

        notify_application_status(application)

        messages.success(request, 'Application marked as Under Review.')

    elif action == 'verified':
        application.processing_status = 'approved'
        application.document_status = 'verified'
        application.review_notes = 'Documents verified successfully.'
        application.save()

        notify_application_status(application)

        messages.success(request, 'Application marked as Verified.')

    elif action == 'incomplete':
        application.processing_status = 'under_review'
        application.document_status = 'incomplete'
        application.review_notes = 'Application is incomplete. Additional correction or document update is required.'
        application.save()

        notify_application_status(application)

        messages.success(request, 'Application marked as Incomplete.')

    elif action == 'rejected':
        application.processing_status = 'rejected'
        application.review_notes = 'Application was rejected during review.'
        application.save()

        notify_application_status(application)

        messages.success(request, 'Application rejected.')

    else:
        messages.error(request, 'Invalid review action.')

    return redirect('application_review_update', application_id=application.id)


@login_required
def application_review_update(request, application_id):
    if not hasattr(request.user, 'service_officer_profile'):
        messages.error(request, 'You do not have staff access.')
        return redirect('login')

    application = get_object_or_404(Application, id=application_id)

    if request.method == 'POST':
        processing_status = request.POST.get('processing_status', '').strip()
        document_status = request.POST.get('document_status', '').strip()
        review_notes = request.POST.get('review_notes', '').strip()

        if not processing_status:
            messages.error(request, 'Please select a processing status.')
            return redirect('application_review_update', application_id=application.id)

        if not document_status:
            messages.error(request, 'Please select a document status.')
            return redirect('application_review_update', application_id=application.id)

        application.processing_status = processing_status
        application.document_status = document_status
        application.review_notes = review_notes
        application.save()

        notify_application_status(application)

        messages.success(request, 'Application review status updated successfully.')
        return redirect('application_review_list')

    context = {
        'application': application,
    }

    return render(request, 'staffpanel/application_review_update.html', context)