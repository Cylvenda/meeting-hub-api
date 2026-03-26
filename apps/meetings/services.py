from django.db import transaction
from django.utils import timezone

from .models import Attendance, ParticipantSession, MeetingAuditLog


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


@transaction.atomic
def join_meeting(meeting, user, is_verified_member=True):
    open_session = get_open_session(meeting, user)
    if open_session:
        return open_session

    session = ParticipantSession.objects.create(
        meeting=meeting,
        user=user,
    )

    attendance, _ = Attendance.objects.get_or_create(
        meeting=meeting,
        user=user,
        defaults={
            "first_joined_at": session.joined_at,
            "status": "present",
            "is_verified_member": is_verified_member,
        },
    )

    if not attendance.first_joined_at:
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
    open_session = get_open_session(meeting, user)
    if not open_session:
        return None

    open_session.left_at = timezone.now()
    open_session.save()

    attendance, _ = Attendance.objects.get_or_create(
        meeting=meeting,
        user=user,
    )

    sessions = ParticipantSession.objects.filter(
        meeting=meeting, user=user, left_at__isnull=False
    )

    total_seconds = 0
    first_joined_at = None
    last_left_at = None

    for session in sessions:
        duration = (session.left_at - session.joined_at).total_seconds()
        total_seconds += max(duration, 0)

        if first_joined_at is None or session.joined_at < first_joined_at:
            first_joined_at = session.joined_at

        if last_left_at is None or session.left_at > last_left_at:
            last_left_at = session.left_at

    total_minutes = int(total_seconds // 60)

    attendance.first_joined_at = first_joined_at
    attendance.last_left_at = last_left_at
    attendance.total_duration_minutes = total_minutes
    attendance.save()

    log_meeting_action(
        meeting=meeting,
        action="participant_left",
        user=user,
        metadata={"left_at": open_session.left_at.isoformat()},
    )

    return open_session


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

    meeting_duration_minutes = int(
        (meeting.actual_end - meeting.actual_start).total_seconds() // 60
    )

    for attendance in meeting.attendance_records.all():
        attendance.status = calculate_attendance_status(
            attendance.total_duration_minutes,
            meeting_duration_minutes,
        )
        attendance.save()

    log_meeting_action(
        meeting=meeting,
        action="attendance_finalized",
        metadata={"meeting_duration_minutes": meeting_duration_minutes},
    )
