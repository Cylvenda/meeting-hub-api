import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class Meeting(models.Model):
    STATUS_CHOICES = [
        ("scheduled", "Scheduled"),
        ("ongoing", "Ongoing"),
        ("ended", "Ended"),
        ("cancelled", "Cancelled"),
    ]

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    group = models.ForeignKey(
        "groups.Group", on_delete=models.CASCADE, related_name="meetings"
    )
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hosted_meetings",
    )
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField(blank=True, null=True)
    actual_start = models.DateTimeField(blank=True, null=True)
    actual_end = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="scheduled"
    )
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["-scheduled_start"]

    def __str__(self):
        return f"{self.title} - {self.group}"


class AgendaItem(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    meeting = models.ForeignKey(
        Meeting, on_delete=models.CASCADE, related_name="agenda_items"
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    order = models.PositiveIntegerField(default=1)
    allocated_minutes = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)

    class Meta:
        ordering = ["order"]
        unique_together = ("meeting", "order")

    def __str__(self):
        return f"{self.order}. {self.title}"


class Attendance(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    STATUS_CHOICES = [
        ("present", "Present"),
        ("late", "Late"),
        ("left_early", "Left Early"),
        ("absent", "Absent"),
    ]

    meeting = models.ForeignKey(
        Meeting, on_delete=models.CASCADE, related_name="attendance_records"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="meeting_attendance",
    )

    first_joined_at = models.DateTimeField(blank=True, null=True)
    last_left_at = models.DateTimeField(blank=True, null=True)

    total_duration_minutes = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="absent")

    is_verified_member = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("meeting", "user")

    def __str__(self):
        return f"{self.user} - {self.meeting} - {self.status}"


class ParticipantSession(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    meeting = models.ForeignKey(
        Meeting, on_delete=models.CASCADE, related_name="participant_sessions"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="participant_sessions",
    )

    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["joined_at"]

    def __str__(self):
        return f"{self.user} joined {self.meeting}"


class MeetingMinutes(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    meeting = models.OneToOneField(
        Meeting, on_delete=models.CASCADE, related_name="minutes"
    )
    content = models.TextField()
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="prepared_minutes",
    )
    approved = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Minutes for {self.meeting.title}"


class MeetingAuditLog(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    meeting = models.ForeignKey(
        Meeting, on_delete=models.CASCADE, related_name="audit_logs"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    action = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} - {self.meeting.title}"
