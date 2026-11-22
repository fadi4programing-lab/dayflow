from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Task(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tasks')
    goal = models.ForeignKey(
        'Goal',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='tasks',
    )
    title = models.CharField(max_length=255)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    deadline = models.DateField(null=True, blank=True)
    estimated_minutes = models.PositiveIntegerField(default=30)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    postponed_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'deadline'], name='api_task_user_deadline_idx'),
            models.Index(fields=['user', 'completed_at'], name='api_task_user_completed_idx'),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        previous = None
        if not self._state.adding and self.pk:
            previous = (
                Task.objects.filter(pk=self.pk)
                .only('deadline', 'is_completed', 'goal_id')
                .first()
            )

        # Keep completed_at in sync with is_completed.
        if self.is_completed:
            if self.completed_at is None:
                self.completed_at = timezone.now()
        else:
            self.completed_at = None

        # Count a postponement when an incomplete task's deadline moves later.
        if (
            previous
            and not previous.is_completed
            and not self.is_completed
            and previous.deadline
            and self.deadline
            and self.deadline > previous.deadline
        ):
            self.postponed_count = (self.postponed_count or 0) + 1

        update_fields = kwargs.get('update_fields')
        if update_fields is not None:
            update_fields = set(update_fields)
            update_fields.update({'completed_at', 'postponed_count'})
            kwargs['update_fields'] = update_fields

        super().save(*args, **kwargs)

        # Refresh progress for the new goal and, if it changed, the old goal.
        goal_ids = {
            goal_id
            for goal_id in (
                self.goal_id,
                previous.goal_id if previous else None,
            )
            if goal_id
        }
        for goal in Goal.objects.filter(pk__in=goal_ids):
            goal.recalculate_progress()


class Goal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='goals')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    progress = models.PositiveSmallIntegerField(default=0)
    target_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    def recalculate_progress(self):
        """Recalculate progress from linked tasks when the goal has any."""
        total = self.tasks.count()
        if total == 0:
            return self.progress

        completed = self.tasks.filter(is_completed=True).count()
        progress = min(100, max(0, round(completed / total * 100)))

        if progress != self.progress:
            self.progress = progress
            self.save(update_fields=['progress'])

        return self.progress


class TimeBlock(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='timeblocks')
    task = models.ForeignKey(
        'Task',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='time_blocks',
    )
    title = models.CharField(max_length=255)
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    color = models.CharField(max_length=7, default='#7C6AF7')
    is_executed = models.BooleanField(default=False)
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


class DailyPerformanceSnapshot(models.Model):
    """Daily behavioral metrics for a user, one row per calendar day."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='performance_snapshots',
    )
    date = models.DateField()
    tasks_scheduled = models.PositiveIntegerField(default=0)
    tasks_completed = models.PositiveIntegerField(default=0)
    weighted_completion_rate = models.FloatField(default=0.0)
    on_time_ratio = models.FloatField(default=0.0)
    schedule_adherence = models.FloatField(default=0.0)
    daily_score = models.FloatField(default=0.0)
    rolling_consistency_score = models.FloatField(default=0.0)
    streak_days = models.PositiveIntegerField(default=0)
    burnout_risk = models.FloatField(default=0.0)
    day_archetype = models.CharField(max_length=50, blank=True, default='')
    dominant_factor = models.CharField(max_length=100, blank=True, default='')

    class Meta:
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'date'],
                name='uniq_perf_snapshot_user_date',
            )
        ]

    def __str__(self):
        return f"{self.user.username} - {self.date}"
