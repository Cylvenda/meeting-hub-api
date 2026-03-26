from rest_framework import serializers
from .models import (
    Meeting,
    AgendaItem,
    Attendance,
    ParticipantSession,
    MeetingMinutes,
)


class AgendaItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgendaItem
        fields = [
            "id",
            "meeting",
            "title",
            "description",
            "order",
            "allocated_minutes",
            "completed",
        ]
        read_only_fields = ["id"]


class ParticipantSessionSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = ParticipantSession
        fields = ["id", "user", "user_email", "joined_at", "left_at"]
        read_only_fields = ["id", "joined_at", "left_at", "user_email"]


class AttendanceSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Attendance
        fields = [
            "id",
            "meeting",
            "user",
            "user_email",
            "first_joined_at",
            "last_left_at",
            "total_duration_minutes",
            "status",
            "is_verified_member",
        ]
        read_only_fields = [
            "id",
            "first_joined_at",
            "last_left_at",
            "total_duration_minutes",
            "status",
            "is_verified_member",
            "user_email",
        ]


class MeetingMinutesSerializer(serializers.ModelSerializer):
    prepared_by_email = serializers.EmailField(
        source="prepared_by.email", read_only=True
    )

    class Meta:
        model = MeetingMinutes
        fields = [
            "id",
            "meeting",
            "content",
            "prepared_by",
            "prepared_by_email",
            "approved",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "prepared_by",
            "prepared_by_email",
            "created_at",
            "updated_at",
        ]


class MeetingSerializer(serializers.ModelSerializer):
    host_email = serializers.EmailField(source="host.email", read_only=True)
    agenda_items = AgendaItemSerializer(many=True, read_only=True)
    minutes = MeetingMinutesSerializer(read_only=True)

    class Meta:
        model = Meeting
        fields = [
            "id",
            "title",
            "description",
            "group",
            "host",
            "host_email",
            "scheduled_start",
            "scheduled_end",
            "actual_start",
            "actual_end",
            "status",
            "is_locked",
            "agenda_items",
            "minutes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "host",
            "host_email",
            "actual_start",
            "actual_end",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        scheduled_start = attrs.get("scheduled_start")
        scheduled_end = attrs.get("scheduled_end")

        if scheduled_end and scheduled_start and scheduled_end <= scheduled_start:
            raise serializers.ValidationError(
                {"scheduled_end": "Scheduled end must be after scheduled start."}
            )

        return attrs
