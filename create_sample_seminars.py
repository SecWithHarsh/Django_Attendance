import os
import django
import sys

# Add the project directory to Python path
sys.path.append('d:/College_Project/qr_attendance_django')

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'qr_attendance.settings')
django.setup()

from attendance.models import Seminar
from django.utils import timezone
from datetime import datetime, timedelta

# Create test seminars with different statuses
now = timezone.now()

# Create an active seminar (currently running)
active_seminar = Seminar.objects.create(
    seminar_id="SEM001",
    title="Introduction to Python Programming",
    start_time=now - timedelta(minutes=30),  # Started 30 minutes ago
    end_time=now + timedelta(minutes=30)     # Ends in 30 minutes
)

# Create an upcoming seminar
upcoming_seminar = Seminar.objects.create(
    seminar_id="SEM002", 
    title="Advanced Django Development",
    start_time=now + timedelta(hours=2),     # Starts in 2 hours
    end_time=now + timedelta(hours=4)       # Ends in 4 hours
)

# Create an ended seminar
ended_seminar = Seminar.objects.create(
    seminar_id="SEM003",
    title="Database Design Fundamentals", 
    start_time=now - timedelta(hours=3),     # Started 3 hours ago
    end_time=now - timedelta(hours=1)       # Ended 1 hour ago
)

print("✅ Sample seminars created successfully!")
print(f"🔴 Active Seminar: {active_seminar.seminar_id} - {active_seminar.title}")
print(f"🟡 Upcoming Seminar: {upcoming_seminar.seminar_id} - {upcoming_seminar.title}")
print(f"⚫ Ended Seminar: {ended_seminar.seminar_id} - {ended_seminar.title}")
print("\n📝 You can now see different statuses in the Seminars page!")
