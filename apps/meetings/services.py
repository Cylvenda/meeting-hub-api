from django.conf import settings
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from django.core.mail import EmailMultiAlternatives

from .models import Attendance, ParticipantSession, MeetingAuditLog


def send_templated_email(*, subject, to, text_template, html_template, context):
    text_body = render_to_string(text_template, context)
    html_body = render_to_string(html_template, context)

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to,
    )
    email.attach_alternative(html_body, "text/html")
    email.send(fail_silently=False)


def get_meeting_notification_recipients(meeting):
    return list(
        meeting.group.memberships.filter(
            is_active=True,
            is_verified=True,
        )
        .exclude(user=meeting.host)
        .select_related("user")
    )


def get_meeting_portal_url(meeting):
    return f"{settings.FRONTEND_URL}/meeting/{meeting.uuid}"


def get_meeting_session_url(meeting):
    return f"{settings.FRONTEND_URL}/meeting/{meeting.uuid}/session"


def send_meeting_scheduled_email(meeting):
    recipients = get_meeting_notification_recipients(meeting)
    if not recipients:
        return

    subject = f"New meeting scheduled: {meeting.title}"
    scheduled_start = timezone.localtime(meeting.scheduled_start)
    scheduled_end = (
        timezone.localtime(meeting.scheduled_end) if meeting.scheduled_end else None
    )

    for membership in recipients:
        context = {
            "site_name": settings.SITE_NAME,
            "recipient_email": membership.user.email,
            "meeting_title": meeting.title,
            "meeting_description": meeting.description,
            "group_name": meeting.group.name,
            "host_name": meeting.host.full_name.strip() or meeting.host.email,
            "scheduled_start": scheduled_start,
            "scheduled_end": scheduled_end,
            "meeting_url": get_meeting_portal_url(meeting),
            "action_label": "View Meeting Details",
            "headline": "A new meeting has been scheduled",
            "summary": "A new group meeting has been created. Review the details and prepare to join on time.",
        }
        send_templated_email(
            subject=subject,
            to=[membership.user.email],
            text_template="email/meeting_scheduled.txt",
            html_template="email/meeting_scheduled.html",
            context=context,
        )


def send_meeting_started_email(meeting, *, instant=False):
    recipients = get_meeting_notification_recipients(meeting)
    if not recipients:
        return

    subject = f"Meeting is live now: {meeting.title}"
    actual_start = timezone.localtime(meeting.actual_start or timezone.now())

    for membership in recipients:
        context = {
            "site_name": settings.SITE_NAME,
            "recipient_email": membership.user.email,
            "meeting_title": meeting.title,
            "meeting_description": meeting.description,
            "group_name": meeting.group.name,
            "host_name": meeting.host.full_name.strip() or meeting.host.email,
            "scheduled_start": actual_start,
            "scheduled_end": None,
            "meeting_url": get_meeting_session_url(meeting),
            "action_label": "Join Meeting Now",
            "headline": "An instant meeting is now live" if instant else "Your meeting has started",
            "summary": (
                "The host started an instant meeting for your group. Join now to participate live."
                if instant
                else "The scheduled meeting is now live. Join now to participate."
            ),
        }
        send_templated_email(
            subject=subject,
            to=[membership.user.email],
            text_template="email/meeting_started.txt",
            html_template="email/meeting_started.html",
            context=context,
        )


def log_meeting_action(meeting, action, user=None, metadata=None):
    MeetingAuditLog.objects.create(
        meeting=meeting,
        user=user,
        action=action,
        metadata=metadata or {},
    )


def get_open_session(meeting, user):
    return (
        ParticipantSession.objects.filter(
            meeting=meeting, user=user, left_at__isnull=True
        )
        .order_by("-joined_at")
        .first()
    )


def is_verified_meeting_attendee(meeting, user):
    if meeting.host == user:
        return True

    return meeting.group.memberships.filter(
        user=user,
        is_verified=True,
        is_active=True,
    ).exists()


def get_authorized_meeting_attendees(meeting):
    attendees = {str(meeting.host.uuid): meeting.host}

    for membership in (
        meeting.group.memberships.filter(is_verified=True, is_active=True)
        .select_related("user")
    ):
        attendees[str(membership.user.uuid)] = membership.user

    return list(attendees.values())


@transaction.atomic
def join_meeting(meeting, user, is_verified_member=True):
    # Lock to prevent duplicate session creation
    open_session = (
        ParticipantSession.objects.select_for_update()
        .filter(meeting=meeting, user=user, left_at__isnull=True)
        .first()
    )

    if open_session:
        return open_session

    session = ParticipantSession.objects.create(
        meeting=meeting,
        user=user,
    )

    attendance, created = Attendance.objects.get_or_create(
        meeting=meeting,
        user=user,
        defaults={
            "first_joined_at": session.joined_at,
            "status": "present",
            "is_verified_member": is_verified_member,
        },
    )

    # Ensure first join is always recorded correctly
    if not created:
        if attendance.first_joined_at is None:
            attendance.first_joined_at = session.joined_at

        attendance.is_verified_member = is_verified_member
        attendance.status = "present"
        attendance.save()

    log_meeting_action(
        meeting=meeting,
        action="participant_joined",
        user=user,
        metadata={"joined_at": session.joined_at.isoformat()},
    )

    return session


@transaction.atomic
def leave_meeting(meeting, user):
    session = (
        ParticipantSession.objects.select_for_update()
        .filter(meeting=meeting, user=user, left_at__isnull=True)
        .first()
    )

    if not session:
        return None

    now = timezone.now()
    effective_left_at = now
    if meeting.actual_end:
        effective_left_at = min(now, meeting.actual_end)

    if effective_left_at < session.joined_at:
        effective_left_at = session.joined_at

    session.left_at = effective_left_at
    session.save()

    attendance, _ = Attendance.objects.get_or_create(
        meeting=meeting,
        user=user,
    )

    # Only calculate current session impact
    session_duration = (session.left_at - session.joined_at).total_seconds()

    attendance.total_duration_minutes += int(session_duration // 60)

    if attendance.first_joined_at is None:
        attendance.first_joined_at = session.joined_at

    attendance.last_left_at = effective_left_at
    attendance.status = "present"  # temporary until finalization
    attendance.is_verified_member = is_verified_meeting_attendee(meeting, user)
    attendance.save()

    log_meeting_action(
        meeting=meeting,
        action="participant_left",
        user=user,
        metadata={"left_at": now.isoformat()},
    )

    return session


def calculate_attendance_status(total_minutes, meeting_duration_minutes):
    if meeting_duration_minutes <= 0:
        return "absent"

    ratio = total_minutes / meeting_duration_minutes

    if ratio >= 0.75:
        return "present"
    if ratio >= 0.40:
        return "late"
    return "absent"


@transaction.atomic
def finalize_meeting_attendance(meeting):
    if not meeting.actual_start or not meeting.actual_end:
        return

    open_sessions = list(
        ParticipantSession.objects.select_for_update().filter(
            meeting=meeting, left_at__isnull=True
        )
    )

    for session in open_sessions:
        session.left_at = meeting.actual_end

    if open_sessions:
        ParticipantSession.objects.bulk_update(open_sessions, ["left_at"])

        for session in open_sessions:
            attendance, _ = Attendance.objects.get_or_create(
                meeting=meeting,
                user=session.user,
                defaults={
                    "first_joined_at": session.joined_at,
                    "status": "present",
                    "is_verified_member": is_verified_meeting_attendee(
                        meeting, session.user
                    ),
                },
            )

            session_duration = max(
                0, int((session.left_at - session.joined_at).total_seconds() // 60)
            )
            attendance.total_duration_minutes += session_duration
            if attendance.first_joined_at is None:
                attendance.first_joined_at = session.joined_at
            if (
                attendance.last_left_at is None
                or session.left_at > attendance.last_left_at
            ):
                attendance.last_left_at = session.left_at
            attendance.is_verified_member = is_verified_meeting_attendee(
                meeting, session.user
            )
            attendance.save()

    for user in get_authorized_meeting_attendees(meeting):
        Attendance.objects.get_or_create(
            meeting=meeting,
            user=user,
            defaults={
                "status": "absent",
                "is_verified_member": True,
            },
        )

    meeting_duration_minutes = int(
        (meeting.actual_end - meeting.actual_start).total_seconds() // 60
    )

    attendances = Attendance.objects.filter(meeting=meeting)

    for attendance in attendances:
        attendance.status = calculate_attendance_status(
            attendance.total_duration_minutes,
            meeting_duration_minutes,
        )

    Attendance.objects.bulk_update(attendances, ["status"])

    log_meeting_action(
        meeting=meeting,
        action="attendance_finalized",
        metadata={"meeting_duration_minutes": meeting_duration_minutes},
    )
