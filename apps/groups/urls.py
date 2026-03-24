from django.urls import path
from .views import (
    GroupListCreateView,
    GroupDetailView,
    AddGroupMemberView,
    GroupMemberListView,
    VerifyGroupMemberView,
    ToggleGroupMemberActiveView,
    SendGroupInvitationView,
    MyInvitationsView,
    RespondInvitationView,
)

urlpatterns = [
    path("", GroupListCreateView.as_view(), name="group-list-create"),
    path("<uuid:uuid>/", GroupDetailView.as_view(), name="group-detail"),
    path(
        "<uuid:uuid>/members/",
        GroupMemberListView.as_view(),
        name="group-member-list",
    ),
    path(
        "<uuid:group_uuid>/members/add/",
        AddGroupMemberView.as_view(),
        name="group-add-member",
    ),
    path(
        "<uuid:group_uuid>/members/<uuid:membership_uuid>/verify/",
        VerifyGroupMemberView.as_view(),
        name="group-member-verify",
    ),
    path(
        "<uuid:group_uuid>/members/<uuid:membership_uuid>/activate/",
        ToggleGroupMemberActiveView.as_view(),
        name="group-member-activate",
    ),
    path(
        "groups/<uuid:group_uuid>/invite/",
        SendGroupInvitationView.as_view(),
        name="send-group-invitations-emails",
    ),
    path(
        "my-invitations/",
        MyInvitationsView.as_view(),
        name="listing-all-my-invitations",
        
    ),
    path(
        "invitations/<uuid:invitation_uuid>/respond/",
        RespondInvitationView.as_view(),
        name="user-invitations-responds",
    ),
]
