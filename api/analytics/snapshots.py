"""Shared snapshot refresh helpers used by signals and management commands."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
from django.db.models import Min
from django.utils import timezone

from ..models import CalendarTask, DailyPerformanceSnapshot, Task, TimeBlock
from . import features, scoring


def _as_date(value: date | datetime | str | None, default: date | None = None) -> date:
    if value is None:
        if default is None:
            raise ValueError("A date value is required.")
        return default
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise TypeError(f"Unsupported date value: {value!r}")


def _row_date(row: pd.Series) -> date:
    return _as_date(row["date"])


def _has_activity(row: pd.Series) -> bool:
    return any(
        int(row.get(column, 0) or 0) > 0
        for column in ("tasks_scheduled", "tasks_completed", "blocks_scheduled")
    )


def snapshot_defaults(row: pd.Series) -> dict[str, Any]:
    """Map a scored daily row onto DailyPerformanceSnapshot fields."""
    return {
        "tasks_scheduled": int(row.get("tasks_scheduled", 0) or 0),
        "tasks_completed": int(row.get("tasks_completed", 0) or 0),
        "weighted_completion_rate": float(
            row.get("weighted_completion_rate", 0.0) or 0.0
        ),
        "on_time_ratio": float(row.get("on_time_ratio", 0.0) or 0.0),
        "schedule_adherence": float(row.get("schedule_adherence", 0.0) or 0.0),
        "daily_score": float(row.get("daily_score", 0.0) or 0.0),
        "rolling_consistency_score": float(
            row.get("rolling_consistency_score", 0.0) or 0.0
        ),
        "streak_days": int(row.get("streak_days", 0) or 0),
        "burnout_risk": float(row.get("burnout_risk_score", 0.0) or 0.0),
        "day_archetype": str(row.get("heuristic_day_archetype", "") or ""),
        "dominant_factor": str(row.get("dominant_factor", "") or ""),
    }


def _find_row(daily: pd.DataFrame, day: date) -> pd.Series | None:
    for _, row in daily.sort_values("date").iterrows():
        if _row_date(row) == day:
            return row
    return None


def refresh_snapshot_for_date(
    user,
    day: date | datetime | str | None = None,
    *,
    lookback_days: int = scoring.CONSISTENCY_WINDOW_DAYS + 1,
) -> DailyPerformanceSnapshot | None:
    """Refresh one day's snapshot. Empty days remove any stale snapshot."""
    target = _as_date(day, default=timezone.localdate())
    start = target - timedelta(days=max(1, int(lookback_days)))
    daily = features.build_daily_frame(user, start, target)
    if daily.empty:
        return None

    row = _find_row(daily, target)
    if row is None or not _has_activity(row):
        DailyPerformanceSnapshot.objects.filter(user=user, date=target).delete()
        return None

    snapshot, _ = DailyPerformanceSnapshot.objects.update_or_create(
        user=user,
        date=target,
        defaults=snapshot_defaults(row),
    )
    return snapshot


def _earliest_activity_date(user, end: date) -> date:
    """Return the earliest relevant day across snapshots, tasks, and blocks."""
    candidates: list[date] = []

    snapshot_min = DailyPerformanceSnapshot.objects.filter(user=user).aggregate(
        value=Min("date")
    )["value"]
    task_min = Task.objects.filter(user=user, deadline__isnull=False).aggregate(
        value=Min("deadline")
    )["value"]
    calendar_min = CalendarTask.objects.filter(user=user).aggregate(
        value=Min("date")
    )["value"]
    block_min = TimeBlock.objects.filter(user=user).aggregate(
        value=Min("date")
    )["value"]

    for value in (snapshot_min, task_min, calendar_min, block_min):
        if value is not None:
            candidates.append(value)

    earliest = min(candidates) if candidates else end - timedelta(days=29)
    return min(earliest, end)


def recalculate_user_snapshots(
    user,
    *,
    days: int | None = 30,
    end_date: date | datetime | str | None = None,
) -> dict[str, int]:
    """Rebuild snapshots for a user.

    Pass ``days=None`` to recalculate the user's full available history.
    """
    end = _as_date(end_date, default=timezone.localdate())

    if days is None:
        start = _earliest_activity_date(user, end)
    else:
        window_days = max(1, int(days))
        start = end - timedelta(days=window_days - 1)

    history_start = start - timedelta(days=scoring.CONSISTENCY_WINDOW_DAYS + 1)

    daily = features.build_daily_frame(user, history_start, end)
    if daily.empty:
        return {"created": 0, "updated": 0, "skipped": 0, "snapshots": 0}

    created = 0
    updated = 0
    skipped = 0

    for _, row in daily.iterrows():
        day = _row_date(row)
        if day < start or day > end:
            continue
        if not _has_activity(row):
            skipped += 1
            continue

        _, was_created = DailyPerformanceSnapshot.objects.update_or_create(
            user=user,
            date=day,
            defaults=snapshot_defaults(row),
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "snapshots": DailyPerformanceSnapshot.objects.filter(
            user=user,
            date__gte=start,
            date__lte=end,
        ).count(),
    }
