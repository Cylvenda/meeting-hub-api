import logging
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings

from apps.notifications.services import create_notification
from apps.notifications.models import Notification

User = get_user_model()
logger = logging.getLogger(__name__)


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
        f"Your membership in '{group.name}' has been verified.\n"
        f"You can now participate as a verified member."
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def notify_invitation_sent(invitation):
    try:
        send_group_invitation_email(invitation)
    except Exception:
        logger.exception(
            "Failed to send invitation email for invitation %s", invitation.uuid
        )

    existing_user = User.objects.filter(email=invitation.email).first()
    if existing_user:
        create_notification(
            user=existing_user,
            title="New Group Invitation",
            message=f"You have been invited to join '{invitation.group.name}'.",
            notification_type=Notification.NotificationType.GROUP_INVITATION,
            group_uuid=invitation.group.uuid,
            invitation_uuid=invitation.uuid,
        )


def notify_invitation_accepted(invitation):
    try:
        create_notification(
            user=invitation.invited_by,
            title="Invitation Accepted",
            message=f"{invitation.email} accepted the invitation to join '{invitation.group.name}'.",
            notification_type=Notification.NotificationType.INVITATION_ACCEPTED,
            group_uuid=invitation.group.uuid,
            invitation_uuid=invitation.uuid,
        )
    except Exception:
        logger.exception(
            "Failed to create acceptance notification for invitation %s",
            invitation.uuid,
        )


def notify_invitation_declined(invitation):
    try:
        create_notification(
            user=invitation.invited_by,
            title="Invitation Declined",
            message=f"{invitation.email} declined the invitation to join '{invitation.group.name}'.",
            notification_type=Notification.NotificationType.GENERAL,
            group_uuid=invitation.group.uuid,
            invitation_uuid=invitation.uuid,
        )
    except Exception:
        logger.exception(
            "Failed to create decline notification for invitation %s", invitation.uuid
        )
