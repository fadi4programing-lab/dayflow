"""Signals that keep today's behavioral snapshot in sync with user activity."""

from __future__ import annotations

import logging

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from .analytics.snapshots import refresh_snapshot_for_date
from .models import Task, TimeBlock

logger = logging.getLogger(__name__)


def _refresh_today(instance) -> None:
    user_id = getattr(instance, "user_id", None)
    if not user_id:
        return
    try:
        user = instance.user
    except Exception:
        return

    try:
        refresh_snapshot_for_date(user, timezone.localdate())
    except Exception:
        logger.exception(
            "Failed to refresh today's analytics snapshot for user %s",
            user_id,
        )


@receiver(
    post_save,
    sender=Task,
    dispatch_uid="api.task_saved_refresh_snapshot",
)
def task_saved(sender, instance, raw=False, **kwargs):
    if raw:
        return
    _refresh_today(instance)


@receiver(
    post_delete,
    sender=Task,
    dispatch_uid="api.task_deleted_refresh_snapshot",
)
def task_deleted(sender, instance, **kwargs):
    _refresh_today(instance)


@receiver(
    post_save,
    sender=TimeBlock,
    dispatch_uid="api.timeblock_saved_refresh_snapshot",
)
def timeblock_saved(sender, instance, raw=False, **kwargs):
    if raw:
        return
    _refresh_today(instance)


@receiver(
    post_delete,
    sender=TimeBlock,
    dispatch_uid="api.timeblock_deleted_refresh_snapshot",
)
def timeblock_deleted(sender, instance, **kwargs):
    _refresh_today(instance)
