from rest_framework import serializers
from .models import Group, GroupMembership, GroupInvitation
from django.contrib.auth import get_user_model

User = get_user_model()


class GroupMembershipSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.uuid", read_only=True)
    group_id = serializers.UUIDField(source="group.uuid", read_only=True)
    membership_id = serializers.UUIDField(source="uuid", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)

    class Meta:
        model = GroupMembership
        fields = [
            "group_id",
            "user_id",
            "membership_id",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "is_verified",
            "joined_at",
        ]


class GroupSerializer(serializers.ModelSerializer):
    group_id = serializers.UUIDField(source="uuid", read_only=True)
    created_by = serializers.EmailField(source="created_by.email", read_only=True)
    memberships = GroupMembershipSerializer(many=True, read_only=True)
    members_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = [
            "group_id",
            "name",
            "description",
            "created_by",
            "is_active",
            "is_private",
            "members_count",
            "memberships",
            "created_at",
            "updated_at",
        ]

    def get_members_count(self, obj):
        return obj.memberships.count()


class GroupCreateSerializer(serializers.ModelSerializer):
    group_id = serializers.UUIDField(source="uuid", read_only=True)

    class Meta:
        model = Group
        fields = [
            "group_id",
            "name",
            "description",
            "is_active",
            "is_private",
        ]
        read_only_fields = ["group_id"]

    def create(self, validated_data):
        request = self.context["request"]

        group = Group.objects.create(created_by=request.user, **validated_data)

        GroupMembership.objects.create(
            user=request.user,
            group=group,
            role=GroupMembership.Role.HOST,
            is_active=True,
            is_verified=True,
        )

        return group


class AddGroupMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role = serializers.ChoiceField(
        choices=GroupMembership.Role.choices, default=GroupMembership.Role.MEMBER
    )

    # Check user exists
    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError("User does not exist.")
        return value

    # Prevent duplicate membership
    def validate(self, attrs):
        group = self.context["group"]

        user_id = attrs.get("user_id")
        if not user_id:
            raise serializers.ValidationError({"user_id": "This field is required."})

        if GroupMembership.objects.filter(group=group, user_id=user_id).exists():
            raise serializers.ValidationError("User is already a member of this group.")

        return attrs

    # Create membership
    def create(self, validated_data):
        group = self.context["group"]
        user = User.objects.get(id=validated_data["user_id"])

        membership = GroupMembership.objects.create(
            user=user,
            group=group,
            role=validated_data.get("role", GroupMembership.Role.MEMBER),
            is_active=True,
            is_verified=False,  # IMPORTANT for your system
        )

        return membership

class SendInvitationSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        email = attrs["email"]
        group = self.context["group"]

        # check already a member
        user = User.objects.filter(email=email).first()
        if user and GroupMembership.objects.filter(group=group, user=user).exists():
            raise serializers.ValidationError("User is already a member.")

        # check existing invitation
        if GroupInvitation.objects.filter(
            group=group, email=email, status=GroupInvitation.Status.PENDING
        ).exists():
            raise serializers.ValidationError("Invitation already sent.")

        return attrs

    def create(self, validated_data):
        group = self.context["group"]
        user = self.context["request"].user

        invitation = GroupInvitation.objects.create(
            group=group, email=validated_data["email"], invited_by=user
        )

        return invitation

# verify group members
class VerifyGroupMemberSerializer(serializers.Serializer):
    pass


# changing group member status
class ToggleGroupMemberActiveSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


class RespondInvitationSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "decline"])


class GroupInvitationSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(source="group.name", read_only=True)

    class Meta:
        model = GroupInvitation
        fields = [
            "uuid",
            "group_name",
            "email",
            "status",
            "created_at",
        ]
