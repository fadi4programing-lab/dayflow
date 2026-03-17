from apscheduler.schedulers.background import BackgroundScheduler
from django_apscheduler.jobstores import DjangoJobStore
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings


def send_notifications():
    """Runs every day — checks for tasks & events due today and sends emails"""
    from .models import CalendarTask, Event

    today = timezone.now().date()

    # ── Calendar Tasks ──
    due_tasks = CalendarTask.objects.filter(
        date=today,
        notify_by_email=True,
        notification_sent=False,
        task__is_completed=False
    ).select_related('user', 'task')

    for entry in due_tasks:
        if entry.user.email:
            send_mail(
                subject=f" Task Reminder: {entry.task.title}",
                message=f"""
Hi {entry.user.username},

This is a reminder that your task is due today!

    Task: {entry.task.title}
    Date: {entry.date}
    Priority: {entry.task.priority.upper()}

Open dayflow to mark it complete.

— dayflow team
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[entry.user.email],
                fail_silently=False,
            )
            entry.notification_sent = True
            entry.save()

    # ── Events ──
    due_events = Event.objects.filter(
        date=today,
        notify_by_email=True,
        notification_sent=False,
        is_completed=False
    ).select_related('user')

    for event in due_events:
        if event.user.email:
            send_mail(
                subject=f" Event Today: {event.title}",
                message=f"""
Hi {event.user.username},

You have an event scheduled for today!

    Event: {event.title}
    Description: {event.description or 'No description'}
    Time: {event.start_time or 'All day'}
    Type: {event.event_type.upper()}

Open dayflow to view details.

— dayflow team
                """,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[event.user.email],
                fail_silently=False,
            )
            event.notification_sent = True
            event.save()

    print(f"[dayflow] Notifications sent for {today}")


def start():
    scheduler = BackgroundScheduler()
    scheduler.add_jobstore(DjangoJobStore(), "default")
    scheduler.add_job(
        send_notifications,
        'cron',
        hour=8,          #  runs every day at 8:00 AM
        minute=0,
        id='send_notifications',
        replace_existing=True,
    )
    scheduler.start()
    print("[dayflow] Scheduler started ")