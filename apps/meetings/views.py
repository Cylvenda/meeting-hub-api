from django.db.models import Q
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Meeting, AgendaItem, Attendance, MeetingMinutes
from .serializers import (
    MeetingSerializer,
    AgendaItemSerializer,
    AttendanceSerializer,
    MeetingMinutesSerializer,
)
from .permissions import IsHostOrVerifiedMemberReadOnly
from .services import (
    join_meeting,
    leave_meeting,
    finalize_meeting_attendance,
    log_meeting_action,
)


class MeetingViewSet(viewsets.ModelViewSet):
    serializer_class = MeetingSerializer
    permission_classes = [IsAuthenticated, IsHostOrVerifiedMemberReadOnly]

    def get_queryset(self):
        user = self.request.user

        return Meeting.objects.filter(
            Q(host=user)
            | Q(
                group__memberships__user=user,
                group__memberships__is_verified=True,
                group__memberships__is_active=True,
            )
        ).distinct()

    def perform_create(self, serializer):
        meeting = serializer.save(host=self.request.user)
        log_meeting_action(
            meeting=meeting,
            action="meeting_created",
            user=self.request.user,
        )

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        meeting = self.get_object()

        if meeting.host != request.user:
            return Response(
                {"detail": "Only the host can start this meeting."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if meeting.status != "scheduled":
            return Response(
                {"detail": "Only scheduled meetings can be started."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        meeting.status = "ongoing"
        meeting.actual_start = timezone.now()
        meeting.save(update_fields=["status", "actual_start", "updated_at"])

        log_meeting_action(
            meeting=meeting,
            action="meeting_started",
            user=request.user,
            metadata={"actual_start": meeting.actual_start.isoformat()},
        )

        return Response({"detail": "Meeting started successfully."})

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        meeting = self.get_object()

        if meeting.host != request.user:
            return Response(
                {"detail": "Only the host can end this meeting."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if meeting.status != "ongoing":
            return Response(
                {"detail": "Only ongoing meetings can be ended."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        meeting.status = "ended"
        meeting.actual_end = timezone.now()
        meeting.save(update_fields=["status", "actual_end", "updated_at"])

        finalize_meeting_attendance(meeting)

        log_meeting_action(
            meeting=meeting,
            action="meeting_ended",
            user=request.user,
            metadata={"actual_end": meeting.actual_end.isoformat()},
        )

        return Response({"detail": "Meeting ended successfully."})

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        meeting = self.get_object()

        if meeting.status != "ongoing":
            return Response(
                {"detail": "Meeting is not currently ongoing."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership_exists = meeting.group.memberships.filter(
            user=request.user, is_verified=True, is_active=True
        ).exists()

        if not membership_exists:
            return Response(
                {"detail": "You are not an authorized verified member of this group."},
                status=status.HTTP_403_FORBIDDEN,
            )

        join_meeting(meeting, request.user, is_verified_member=True)

        return Response({"detail": "Joined meeting successfully."})

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        meeting = self.get_object()

        session = leave_meeting(meeting, request.user)
        if not session:
            return Response(
                {"detail": "No active meeting session found for this user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"detail": "Left meeting successfully."})

    @action(detail=True, methods=["get"])
    def attendance(self, request, pk=None):
        meeting = self.get_object()
        attendance_qs = meeting.attendance_records.select_related("user")
        serializer = AttendanceSerializer(attendance_qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get", "post", "patch"])
    def minutes(self, request, pk=None):
        meeting = self.get_object()

        if request.method == "GET":
            minutes = getattr(meeting, "minutes", None)
            if not minutes:
                return Response(
                    {"detail": "Minutes not found."}, status=status.HTTP_404_NOT_FOUND
                )
            serializer = MeetingMinutesSerializer(minutes)
            return Response(serializer.data)

        if request.user != meeting.host:
            return Response(
                {"detail": "Only the host can create or update minutes."},
                status=status.HTTP_403_FORBIDDEN,
            )

        minutes = getattr(meeting, "minutes", None)

        if request.method == "POST":
            if minutes:
                return Response(
                    {"detail": "Minutes already exist for this meeting."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            serializer = MeetingMinutesSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(meeting=meeting, prepared_by=request.user)

            log_meeting_action(
                meeting=meeting,
                action="minutes_created",
                user=request.user,
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == "PATCH":
            if not minutes:
                return Response(
                    {"detail": "Minutes not found."}, status=status.HTTP_404_NOT_FOUND
                )

            serializer = MeetingMinutesSerializer(
                minutes, data=request.data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

            log_meeting_action(
                meeting=meeting,
                action="minutes_updated",
                user=request.user,
            )

            return Response(serializer.data)


class AgendaItemViewSet(viewsets.ModelViewSet):
    queryset = AgendaItem.objects.all()
    serializer_class = AgendaItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return AgendaItem.objects.filter(
            Q(meeting__host=user)
            | Q(
                meeting__group__memberships__user=user,
                meeting__group__memberships__is_verified=True,
                meeting__group__memberships__is_active=True,
            )
        ).distinct()

    def create(self, request, *args, **kwargs):
        meeting_id = request.data.get("meeting")
        if not meeting_id:
            return Response(
                {"detail": "Meeting is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            meeting = Meeting.objects.get(id=meeting_id)
        except Meeting.DoesNotExist:
            return Response(
                {"detail": "Meeting not found."}, status=status.HTTP_404_NOT_FOUND
            )

        if meeting.host != request.user:
            return Response(
                {"detail": "Only the host can add agenda items."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        agenda_item = serializer.save()

        log_meeting_action(
            meeting=agenda_item.meeting,
            action="agenda_item_created",
            user=self.request.user,
            metadata={"agenda_item_id": agenda_item.id, "title": agenda_item.title},
        )

    def perform_update(self, serializer):
        agenda_item = serializer.save()

        log_meeting_action(
            meeting=agenda_item.meeting,
            action="agenda_item_updated",
            user=self.request.user,
            metadata={"agenda_item_id": agenda_item.id, "title": agenda_item.title},
        )

    def perform_destroy(self, instance):
        meeting = instance.meeting
        agenda_item_id = instance.id
        title = instance.title
        instance.delete()

        log_meeting_action(
            meeting=meeting,
            action="agenda_item_deleted",
            user=self.request.user,
            metadata={"agenda_item_id": agenda_item_id, "title": title},
        )
