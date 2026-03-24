from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

from .models import GroupInvitation

User = get_user_model()


def send_group_invitation_email(invitation):
    subject = f"You have been invited to join {invitation.group.name}"
    message = (
        f"You have been invited to join the group '{invitation.group.name}'.\n\n"
        f"Please log in to your account to accept or decline the invitation."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[invitation.email],
        fail_silently=False,
    )


def send_membership_verified_email(user, group):
    subject = f"Your membership in {group.name} has been verified"
    message = (
        f"Hello,\n\n"
        f"Your membership in the group '{group.name}' has been verified successfully.\n"
        f"You can now participate as an approved member."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def create_group_notification(user, title, message, notification_type="group"):
    from apps.notifications.models import Notification

    return Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
    )


def notify_group_invitation_sent(invitation):
    send_group_invitation_email(invitation)

    existing_user = User.objects.filter(email=invitation.email).first()
    if existing_user:
        create_group_notification(
            user=existing_user,
            title="New Group Invitation",
            message=f"You have been invited to join '{invitation.group.name}'.",
            notification_type="group_invitation",
        )


def notify_group_invitation_accepted(invitation):
    host_user = invitation.invited_by

    create_group_notification(
        user=host_user,
        title="Invitation Accepted",
        message=(
            f"{invitation.email} accepted the invitation to join "
            f"'{invitation.group.name}'."
        ),
        notification_type="group_invitation",
    )


def notify_membership_verified(membership):
    create_group_notification(
        user=membership.user,
        title="Membership Verified",
        message=(
            f"Your membership in '{membership.group.name}' " f"has been verified."
        ),
        notification_type="group_membership",
    )

    send_membership_verified_email(membership.user, membership.group)
