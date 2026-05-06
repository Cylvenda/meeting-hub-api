import os
import django
import uuid

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from apps.accounts.models import User
from apps.groups.models import Group
from apps.meetings.models import Meeting, Attendance, ParticipantSession
from django.utils import timezone

c = Client()
u = User.objects.first()
c.force_login(u)

g = Group.objects.first()

print("--- Testing Instant Meeting Flow ---")
res = c.post('/api/meetings/instant/', {'group': str(g.uuid), 'title': 'Test Instant'})
print("Instant Meeting Response:", res.status_code)
meeting_uuid = res.json()['id']
m = Meeting.objects.get(uuid=meeting_uuid)

print("Attendance initialized:", list(Attendance.objects.filter(meeting=m).values('user_id', 'status', 'first_joined_at')))

# Join the meeting
res_join = c.post(f'/api/meetings/{meeting_uuid}/join/')
print("Join Response:", res_join.status_code)

print("Attendance after join:", list(Attendance.objects.filter(meeting=m).values('user_id', 'status', 'first_joined_at')))
print("Sessions after join:", list(ParticipantSession.objects.filter(meeting=m).values('user_id', 'joined_at', 'left_at')))

# Leave the meeting
res_leave = c.post(f'/api/meetings/{meeting_uuid}/leave/')
print("Leave Response:", res_leave.status_code)

# End the meeting
res_end = c.post(f'/api/meetings/{meeting_uuid}/end/')
print("End Response:", res_end.status_code)

print("Final Attendance:", list(Attendance.objects.filter(meeting=m).values('user_id', 'status', 'total_duration_minutes', 'first_joined_at')))

