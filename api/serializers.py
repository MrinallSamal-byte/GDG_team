from rest_framework import serializers
from django.conf import settings
from events.models import Event, EventPrize, EventRound
from registrations.models import Registration
from teams.models import Team, TeamMember, TeamJoinRequest, Message
from notifications.models import Notification


class EventSerializer(serializers.ModelSerializer):
    organizer_name = serializers.CharField(source='organizer.display_name', read_only=True)
    registration_count = serializers.IntegerField(read_only=True)
    is_registration_open = serializers.BooleanField(read_only=True)

    class Meta:
        model = Event
        fields = [
            'id', 'title', 'slug', 'description', 'category', 'mode',
            'venue', 'registration_start', 'registration_end',
            'event_start', 'event_end', 'participation_type',
            'min_team_size', 'max_team_size', 'prize_pool_total',
            'has_participation_certificate', 'max_participants',
            'registration_fee', 'status', 'is_featured',
            'organizer_name', 'registration_count', 'is_registration_open',
        ]


class RegistrationSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.display_name', read_only=True)
    user_college = serializers.CharField(source='user.college_name', read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)

    class Meta:
        model = Registration
        fields = [
            'id', 'registration_id', 'registration_type', 'status',
            'looking_for_team', 'preferred_role', 'created_at',
            'user_name', 'user_college', 'event_title',
        ]


class TeamMemberSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.display_name', read_only=True)
    user_initials = serializers.CharField(source='user.initials', read_only=True)

    class Meta:
        model = TeamMember
        fields = ['id', 'user_name', 'user_initials', 'role_in_team', 'joined_at']


class TeamSerializer(serializers.ModelSerializer):
    leader_name = serializers.CharField(source='leader.display_name', read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    spots_remaining = serializers.IntegerField(read_only=True)
    members = TeamMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Team
        fields = [
            'id', 'team_name', 'leader_name', 'max_members',
            'is_open', 'member_count', 'spots_remaining',
            'created_at', 'members',
        ]


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source='sender.display_name', read_only=True)
    sender_initials = serializers.CharField(source='sender.initials', read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'sender_name', 'sender_initials', 'content', 'message_type', 'created_at']


class JoinRequestSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.display_name', read_only=True)

    class Meta:
        model = TeamJoinRequest
        fields = ['id', 'user_name', 'message', 'status', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'notification_type', 'is_read', 'created_at',
                  'reference_id', 'reference_type']
