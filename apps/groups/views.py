from .models import Group, GroupMembership, GroupInvitation
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .serializers import (
    GroupSerializer,
    GroupCreateSerializer,
    AddGroupMemberSerializer,
    GroupMembershipSerializer,
    VerifyGroupMemberSerializer,
    ToggleGroupMemberActiveSerializer,
    SendInvitationSerializer,
    GroupInvitationSerializer,
    RespondInvitationSerializer,
)
from .permissions import is_group_host, get_group_or_404


class GroupListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Group.objects.filter(
                memberships__user=self.request.user,
                memberships__is_active=True,
                memberships__is_verified=True,
            )
            .select_related("created_by")
            .prefetch_related("memberships__user")
            .distinct()
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return GroupCreateSerializer
        return GroupSerializer


# add members to group
class AddGroupMemberView(generics.GenericAPIView):
    serializer_class = AddGroupMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, group_uuid):
        group = get_group_or_404(group_uuid)

        is_group_host(request.user, group)

        serializer = self.get_serializer(data=request.data, context={"group": group})
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()

        return Response(
            GroupMembershipSerializer(membership).data, status=status.HTTP_201_CREATED
        )

# all members of the group
class GroupMemberListView(generics.ListAPIView):
    serializer_class = GroupMembershipSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        group = get_group_or_404(self.kwargs["uuid"])

        is_group_host(self.request.user, group)

        return (
            GroupMembership.objects.filter(group=group)
            .select_related("user")
            .order_by("-joined_at")
        )


# view group details
class GroupDetailView(generics.RetrieveAPIView):
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "uuid"
    lookup_url_kwarg = "uuid"

    def get_queryset(self):
        return (
            Group.objects.filter(
                memberships__user=self.request.user,
                memberships__is_active=True,
                memberships__is_verified=True,
            )
            .select_related("created_by")
            .prefetch_related("memberships__user")
            .distinct()
        )

# verifying group members
class VerifyGroupMemberView(generics.GenericAPIView):
    serializer_class = VerifyGroupMemberSerializer
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, group_uuid, membership_uuid):
        group = get_group_or_404(group_uuid)
        is_group_host(request.user, group)

        membership = get_object_or_404(
            GroupMembership,
            uuid=membership_uuid,
            group=group,
        )

        # method for cheking group member permissions
        is_group_host(request.user, group)

        membership.is_verified = True
        membership.save(update_fields=["is_verified"])

        return Response(
            GroupMembershipSerializer(membership).data,
            status=status.HTTP_200_OK,
        )


# changing group members status [activate & deactivate]
class ToggleGroupMemberActiveView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, group_uuid, membership_uuid):
        group = get_group_or_404(group_uuid)
        is_group_host(request.user, group)

        membership = get_object_or_404(
            GroupMembership,
            uuid=membership_uuid,
            group=group,
        )

        # prevent changing host membership active status through this endpoint
        if membership.role == GroupMembership.Role.HOST:
            return Response(
                {
                    "detail": "Host membership cannot be deactivated through this endpoint."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        membership.is_active = not membership.is_active
        membership.save(update_fields=["is_active"])

        return Response(
            {
                "detail": (
                    "Member activated successfully."
                    if membership.is_active
                    else "Member deactivated successfully."
                ),
                "data": GroupMembershipSerializer(membership).data,
            },
            status=status.HTTP_200_OK,
        )


class SendGroupInvitationView(generics.GenericAPIView):
    serializer_class = SendInvitationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, group_uuid):
        group = get_group_or_404(group_uuid)
        is_group_host(request.user, group)

        serializer = self.get_serializer(
            data=request.data, context={"group": group, "request": request}
        )
        serializer.is_valid(raise_exception=True)
        invitation = serializer.save()

        return Response(
            GroupInvitationSerializer(invitation).data, status=status.HTTP_201_CREATED
        )


class MyInvitationsView(generics.ListAPIView):
    serializer_class = GroupInvitationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return GroupInvitation.objects.filter(
            email=self.request.user.email, status=GroupInvitation.Status.PENDING
        ).select_related("group")


class RespondInvitationView(generics.GenericAPIView):
    serializer_class = RespondInvitationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, invitation_uuid):
        invitation = get_object_or_404(GroupInvitation, uuid=invitation_uuid)

        # security check
        if request.user.email != invitation.email:
            return Response(
                {"detail": "You are not allowed to respond to this invitation."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if invitation.status != GroupInvitation.Status.PENDING:
            return Response(
                {"detail": "Invitation already handled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action = serializer.validated_data["action"]

        if action == "decline":
            invitation.status = GroupInvitation.Status.DECLINED
            invitation.responded_at = timezone.now()
            invitation.save()
            return Response({"detail": "Invitation declined."})

        # ACCEPT
        invitation.status = GroupInvitation.Status.ACCEPTED
        invitation.responded_at = timezone.now()
        invitation.save()

        # create membership
        membership, created = GroupMembership.objects.get_or_create(
            group=invitation.group,
            user=request.user,
            defaults={
                "role": GroupMembership.Role.MEMBER,
                "is_active": True,
                "is_verified": False,
            },
        )

        return Response(
            {"detail": "Invitation accepted.", "membership_id": str(membership.uuid)}
        )
