"""Time-series feature engineering for behavioral performance data."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from django.db.models import Q
from django.utils import timezone

from ..models import Task, TimeBlock
from . import scoring

FEATURE_WINDOWS = (7, 14)

FEATURE_COLUMNS: list[str] = [
    "rolling_completion_rate_7",
    "rolling_completion_rate_14",
    "streak_length_7",
    "streak_length_14",
    "high_priority_delay_ratio_7",
    "high_priority_delay_ratio_14",
    "avg_postponement_rate_7",
    "avg_postponement_rate_14",
    "workload_intensity_7",
    "workload_intensity_14",
    "goal_task_velocity_7",
    "goal_task_velocity_14",
    "schedule_adherence_7",
    "schedule_adherence_14",
    "on_time_ratio_7",
    "on_time_ratio_14",
    "completion_trend_7",
]

DAILY_COLUMNS: list[str] = [
    "user_id",
    "date",
    "tasks_scheduled",
    "tasks_completed",
    "high_scheduled",
    "medium_scheduled",
    "low_scheduled",
    "high_completed",
    "medium_completed",
    "low_completed",
    "high_priority_delayed",
    "postponements",
    "blocks_scheduled",
    "blocks_executed",
    "on_time_completed",
    "completed_with_deadline",
    "goal_tasks_completed",
    "workload_minutes",
]


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


def _local_date(value: datetime | None) -> date | None:
    if value is None:
        return None
    if timezone.is_aware(value):
        return timezone.localtime(value).date()
    return value.date()


def _empty_daily_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=DAILY_COLUMNS)


def apply_heuristic_scores(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Add heuristic daily scores, consistency, streak, and risk columns.

    ``daily_df`` must contain the columns produced by :func:`build_daily_frame`
    (or by the synthetic generator).
    """
    if daily_df.empty:
        return daily_df.copy()

    df = daily_df.sort_values(["user_id", "date"]).reset_index(drop=True).copy()

    score_columns = {
        "weighted_completion_rate": 0.0,
        "on_time_ratio": 0.0,
        "schedule_adherence": 0.0,
        "regularity_factor": 0.0,
        "postponement_penalty": 0.0,
        "daily_score": 0.0,
        "rolling_consistency_score": 0.0,
        "streak_days": 0,
        "burnout_risk_score": 0.0,
        "dominant_factor": "",
        "heuristic_day_archetype": "",
    }
    for column, default in score_columns.items():
        if column not in df.columns:
            df[column] = default

    for user_id, user_df in df.groupby("user_id", sort=False):
        rate_history: list[float] = []
        scores_by_date: dict[date, float] = {}
        streak = 0

        for index, row in user_df.iterrows():
            day = _as_date(row["date"])
            scheduled_map = {
                "high": int(row.get("high_scheduled", 0) or 0),
                "medium": int(row.get("medium_scheduled", 0) or 0),
                "low": int(row.get("low_scheduled", 0) or 0),
            }
            completed_map = {
                "high": int(row.get("high_completed", 0) or 0),
                "medium": int(row.get("medium_completed", 0) or 0),
                "low": int(row.get("low_completed", 0) or 0),
            }

            current_rate = scoring.weighted_completion_rate(
                scheduled_map,
                completed_map,
            )
            recent_rates = (rate_history + [current_rate])[
                -scoring.REGULARITY_WINDOW_DAYS :
            ]

            result = scoring.compute_daily_score(
                scheduled_by_priority=scheduled_map,
                completed_by_priority=completed_map,
                tasks_scheduled=int(row.get("tasks_scheduled", 0) or 0),
                tasks_completed=int(row.get("tasks_completed", 0) or 0),
                on_time_completed=int(row.get("on_time_completed", 0) or 0),
                completed_with_deadline=int(row.get("completed_with_deadline", 0) or 0),
                blocks_scheduled=int(row.get("blocks_scheduled", 0) or 0),
                blocks_executed=int(row.get("blocks_executed", 0) or 0),
                postponed_count=int(row.get("postponements", 0) or 0),
                recent_completion_rates=recent_rates,
            )

            rate_history.append(current_rate)
            scores_by_date[day] = result["daily_score"]
            consistency = scoring.compute_rolling_consistency(
                scores_by_date,
                day,
            )

            completed_today = int(row.get("tasks_completed", 0) or 0)
            streak = streak + 1 if completed_today > 0 else 0

            workload_intensity = float(row.get("workload_minutes", 0) or 0) / 480.0
            scheduled_today = int(row.get("tasks_scheduled", 0) or 0)
            postponement_rate = (
                float(row.get("postponements", 0) or 0) / scheduled_today
                if scheduled_today > 0
                else 0.0
            )
            prior_rates = rate_history[-8:-1]
            completion_trend = (
                current_rate - float(np.mean(prior_rates)) if prior_rates else 0.0
            )

            burnout = scoring.heuristic_burnout_risk(
                workload_intensity=workload_intensity,
                postponement_rate=postponement_rate,
                schedule_adherence=result["schedule_adherence"],
                consistency=consistency,
                completion_trend=completion_trend,
            )
            archetype = scoring.heuristic_day_archetype(
                weighted_completion=result["weighted_completion_rate"],
                workload_intensity=workload_intensity,
                schedule_adherence=result["schedule_adherence"],
                consistency=consistency,
            )

            for column in (
                "weighted_completion_rate",
                "on_time_ratio",
                "schedule_adherence",
                "regularity_factor",
                "postponement_penalty",
                "daily_score",
            ):
                df.at[index, column] = float(result[column])
            df.at[index, "rolling_consistency_score"] = float(consistency)
            df.at[index, "streak_days"] = int(streak)
            df.at[index, "burnout_risk_score"] = float(burnout)
            df.at[index, "dominant_factor"] = result["dominant_factor"]
            df.at[index, "heuristic_day_archetype"] = archetype

    return df


def build_daily_frame(
    user,
    start_date: date | datetime | str | None = None,
    end_date: date | datetime | str | None = None,
) -> pd.DataFrame:
    """Build per-day behavioral metrics for a user from raw Django records.

    A task is considered scheduled on its ``deadline`` and on any calendar day
    where it is pinned through ``CalendarTask``. A task counts as completed on a
    day when its ``completed_at`` date is on or before that day.
    """
    end = _as_date(end_date, default=timezone.localdate())
    start = _as_date(
        start_date,
        default=end - timedelta(days=scoring.CONSISTENCY_WINDOW_DAYS - 1),
    )
    if start > end:
        raise ValueError("start_date must be on or before end_date.")

    tasks = list(
        Task.objects.filter(user=user)
        .filter(
            Q(deadline__range=(start, end))
            | Q(calendar_entries__date__range=(start, end))
        )
        .distinct()
        .prefetch_related("calendar_entries")
    )

    scheduled: dict[date, dict[int, tuple[Task, date | None]]] = defaultdict(dict)
    for task in tasks:
        scheduled_dates: set[date] = set()
        if task.deadline and start <= task.deadline <= end:
            scheduled_dates.add(task.deadline)
        for entry in task.calendar_entries.all():
            if start <= entry.date <= end:
                scheduled_dates.add(entry.date)
        if not scheduled_dates:
            continue

        completion_date: date | None = None
        if task.is_completed:
            if task.completed_at:
                completion_date = _local_date(task.completed_at)
            elif task.deadline:
                completion_date = task.deadline
            else:
                completion_date = min(scheduled_dates)

        for day in scheduled_dates:
            scheduled[day][task.pk] = (task, completion_date)

    blocks: dict[date, list[TimeBlock]] = defaultdict(list)
    for block in TimeBlock.objects.filter(user=user, date__range=(start, end)):
        blocks[block.date].append(block)

    rows: list[dict[str, Any]] = []
    current = start
    while current <= end:
        day_entries = list(scheduled.get(current, {}).values())
        high_scheduled = medium_scheduled = low_scheduled = 0
        high_completed = medium_completed = low_completed = 0
        tasks_completed = 0
        completed_with_deadline = 0
        on_time_completed = 0
        high_priority_delayed = 0
        goal_tasks_completed = 0
        postponements = 0
        workload_minutes = 0

        for task, completion_date in day_entries:
            priority = (task.priority or "medium").strip().lower()
            postponements += max(0, int(task.postponed_count or 0))
            workload_minutes += max(0, int(task.estimated_minutes or 0))

            if priority == "high":
                high_scheduled += 1
            elif priority == "low":
                low_scheduled += 1
            else:
                medium_scheduled += 1

            completed_by_day = (
                task.is_completed
                and completion_date is not None
                and completion_date <= current
            )
            if completed_by_day:
                tasks_completed += 1
                if priority == "high":
                    high_completed += 1
                elif priority == "low":
                    low_completed += 1
                else:
                    medium_completed += 1
                if task.goal_id:
                    goal_tasks_completed += 1

            if task.deadline:
                completed_with_deadline += 1
                if completed_by_day:
                    on_time_completed += 1

            if priority == "high" and not completed_by_day:
                high_priority_delayed += 1

        day_blocks = blocks.get(current, [])
        rows.append(
            {
                "user_id": user.pk,
                "date": current,
                "tasks_scheduled": len(day_entries),
                "tasks_completed": tasks_completed,
                "high_scheduled": high_scheduled,
                "medium_scheduled": medium_scheduled,
                "low_scheduled": low_scheduled,
                "high_completed": high_completed,
                "medium_completed": medium_completed,
                "low_completed": low_completed,
                "high_priority_delayed": high_priority_delayed,
                "postponements": postponements,
                "blocks_scheduled": len(day_blocks),
                "blocks_executed": sum(1 for block in day_blocks if block.is_executed),
                "on_time_completed": on_time_completed,
                "completed_with_deadline": completed_with_deadline,
                "goal_tasks_completed": goal_tasks_completed,
                "workload_minutes": workload_minutes,
            }
        )
        current += timedelta(days=1)

    if not rows:
        return _empty_daily_frame()

    return apply_heuristic_scores(pd.DataFrame(rows))


def _rolling_sum(df: pd.DataFrame, column: str, window: int) -> pd.Series:
    return df.groupby("user_id", sort=False)[column].transform(
        lambda values: values.rolling(window, min_periods=1).sum()
    )


def _rolling_mean(df: pd.DataFrame, column: str, window: int) -> pd.Series:
    return df.groupby("user_id", sort=False)[column].transform(
        lambda values: values.rolling(window, min_periods=1).mean()
    )


def _ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    numerator_values = numerator.to_numpy(dtype=float)
    denominator_values = denominator.to_numpy(dtype=float)
    result = np.zeros_like(numerator_values)
    np.divide(
        numerator_values,
        denominator_values,
        out=result,
        where=denominator_values > 0,
    )
    result *= 100.0
    return pd.Series(np.clip(result, 0.0, 100.0), index=numerator.index)


def build_feature_frame(daily_df: pd.DataFrame) -> pd.DataFrame:
    """Create rolling 7-day and 14-day features from daily metrics."""
    if daily_df.empty:
        return daily_df.copy()

    df = daily_df.sort_values(["user_id", "date"]).reset_index(drop=True).copy()
    if "user_id" not in df.columns:
        df["user_id"] = 0

    for window in FEATURE_WINDOWS:
        df[f"rolling_completion_rate_{window}"] = _rolling_mean(
            df, "weighted_completion_rate", window
        )
        df[f"schedule_adherence_{window}"] = _rolling_mean(
            df, "schedule_adherence", window
        )
        df[f"on_time_ratio_{window}"] = _rolling_mean(df, "on_time_ratio", window)

        df[f"high_priority_delay_ratio_{window}"] = _ratio(
            _rolling_sum(df, "high_priority_delayed", window),
            _rolling_sum(df, "high_scheduled", window),
        )
        df[f"avg_postponement_rate_{window}"] = _ratio(
            _rolling_sum(df, "postponements", window),
            _rolling_sum(df, "tasks_scheduled", window),
        )
        df[f"workload_intensity_{window}"] = (
            _rolling_mean(df, "workload_minutes", window) / 480.0
        )
        df[f"goal_task_velocity_{window}"] = (
            _rolling_sum(df, "goal_tasks_completed", window) / float(window)
        )

    for window in FEATURE_WINDOWS:
        streak_series = pd.Series(0, index=df.index, dtype="int64")
        for _, group in df.groupby("user_id", sort=False):
            streak = 0
            for index, completed in zip(
                group.index,
                group["tasks_completed"].fillna(0).astype(int),
            ):
                streak = streak + 1 if completed > 0 else 0
                streak_series.at[index] = min(streak, window)
        df[f"streak_length_{window}"] = streak_series

    previous_completion = df.groupby("user_id", sort=False)[
        "rolling_completion_rate_7"
    ].shift(7)
    df["completion_trend_7"] = (
        df["rolling_completion_rate_7"] - previous_completion
    ).fillna(0.0)

    for column in FEATURE_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)

    return df


def build_user_feature_frame(
    user,
    as_of: date | datetime | str | None = None,
    *,
    lookback_days: int = 27,
) -> pd.DataFrame:
    """Build features for one user over a recent window."""
    end = _as_date(as_of, default=timezone.localdate())
    start = end - timedelta(days=max(13, int(lookback_days)))
    daily = build_daily_frame(user, start, end)
    return build_feature_frame(daily)


def latest_feature_row(feature_df: pd.DataFrame) -> dict[str, float]:
    """Return the most recent feature row as a plain dictionary."""
    if feature_df.empty:
        return {column: 0.0 for column in FEATURE_COLUMNS}

    row = feature_df.sort_values("date").iloc[-1]
    values: dict[str, float] = {}
    for column in FEATURE_COLUMNS:
        value = row.get(column, 0.0)
        values[column] = float(value) if pd.notna(value) else 0.0
    return values
