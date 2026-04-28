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
    session.left_at = now
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

    attendance.last_left_at = now
    attendance.status = "present"  # temporary until finalization
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
