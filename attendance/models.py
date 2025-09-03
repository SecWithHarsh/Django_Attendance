from django.db import models
from django.utils import timezone
from datetime import datetime

class Student(models.Model):
    student_id = models.CharField(max_length=20, unique=True, help_text="SBU format: SBU123456")
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True, default="", help_text="Phone number with country code")
    course = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.student_id} - {self.name}"
    
    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.student_id.startswith('SBU') or len(self.student_id) != 9:
            raise ValidationError('Student ID must be in SBU format (e.g., SBU123456)')
    
    class Meta:
        verbose_name = "Student"
        verbose_name_plural = "Students"

class Seminar(models.Model):
    STATUS_CHOICES = [
        ('inactive', 'Inactive'),
        ('active', 'Active'),
        ('ended', 'Ended'),
    ]
    
    seminar_id = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=200)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='inactive')
    created_at = models.DateTimeField(auto_now_add=True)

    def is_active(self):
        return self.status == 'active'

    def __str__(self):
        return f"{self.seminar_id} - {self.title}"

class Attendance(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, db_index=True)
    seminar = models.ForeignKey(Seminar, on_delete=models.CASCADE, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        unique_together = ('student', 'seminar')
        indexes = [
            models.Index(fields=['student', 'seminar']),
            models.Index(fields=['seminar', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"

    def __str__(self):
        return f"{self.student.student_id} - {self.seminar.seminar_id} - {self.timestamp}"
