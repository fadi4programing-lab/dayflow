from django.db import models
from django.contrib.auth.models import User


class Task(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    deadline = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    progress = models.IntegerField(default=0)
    target_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class TimeBlock(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='timeblocks')
    title = models.CharField(max_length=255)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    color = models.CharField(max_length=7, default='#7C6AF7')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.date})"


class Note(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class Event(models.Model):
    EVENT_TYPES = [
        ('meeting', 'Meeting'),
        ('focus', 'Focus Block'),
        ('deadline', 'Deadline'),
        ('reminder', 'Reminder'),
        ('personal', 'Personal'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES, default='reminder')
    date = models.DateField()
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    notify_by_email = models.BooleanField(default=True)  # 📧
    notification_sent = models.BooleanField(default=False)  # track if already sent
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} — {self.date}"


class CalendarTask(models.Model):
    """Pins a task to a specific calendar day"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='calendar_tasks')
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='calendar_entries')
    date = models.DateField()
    note = models.TextField(blank=True)
    notify_by_email = models.BooleanField(default=True)  # 📧
    notification_sent = models.BooleanField(default=False)  # track if already sent
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('task', 'date')

    def __str__(self):
        return f"{self.task.title} → {self.date}"