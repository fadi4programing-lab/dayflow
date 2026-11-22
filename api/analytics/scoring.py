"""Weighted heuristic scoring for daily performance and consistency.

The functions in this module are intentionally free of Django imports so they
can be reused by the synthetic-data pipeline, tests, and the hybrid predictor.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta
from typing import Any

PRIORITY_WEIGHTS: dict[str, float] = {
    "high": 3.0,
    "medium": 2.0,
    "low": 1.0,
}

DEFAULT_DECAY_LAMBDA = 0.08
CONSISTENCY_WINDOW_DAYS = 14
REGULARITY_WINDOW_DAYS = 7

COMPLETION_WEIGHT = 0.45
SCHEDULE_WEIGHT = 0.25
ON_TIME_WEIGHT = 0.20
REGULARITY_WEIGHT = 0.10

MAX_POSTPONEMENT_PENALTY = 25.0
POSTPONEMENT_PENALTY_PER_TASK = 4.0

BURNOUT_LOW_THRESHOLD = 34.0
BURNOUT_HIGH_THRESHOLD = 67.0

DEEP_FOCUS = "Deep Focus"
STEADY_FLOW = "Steady Flow"
OVERLOADED_DRIFT = "Overloaded / Drift"


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Clamp a numeric value to a closed range."""
    return max(low, min(high, float(value)))


def priority_weight(priority: str | None) -> float:
    """Return the scoring weight for a task priority."""
    return PRIORITY_WEIGHTS.get((priority or "medium").strip().lower(), 1.0)


def weighted_completion_rate(
    scheduled_by_priority: Mapping[str, int] | None,
    completed_by_priority: Mapping[str, int] | None,
) -> float:
    """Compute a 0-100 completion rate where high-priority tasks matter more."""
    scheduled = scheduled_by_priority or {}
    completed = completed_by_priority or {}

    scheduled_weight = sum(
        priority_weight(priority) * max(0, int(count))
        for priority, count in scheduled.items()
    )
    if scheduled_weight <= 0:
        return 0.0

    completed_weight = sum(
        priority_weight(priority) * max(0, int(count))
        for priority, count in completed.items()
    )
    return clamp(completed_weight / scheduled_weight * 100.0)


def _as_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise TypeError(f"Unsupported date value: {value!r}")


def _regularity_factor(
    recent_completion_rates: Sequence[float] | None,
    tasks_completed: int,
) -> float:
    """Reward steady daily execution and penalise erratic completion spikes.

    The coefficient of variation is used because it is scale-independent: a
    user who alternates between 20% and 100% completion is less consistent than
    a user who stays near 60% every day.
    """
    rates = [float(rate) for rate in (recent_completion_rates or [])]
    if not rates:
        return 100.0 if tasks_completed > 0 else 0.0
    if len(rates) == 1:
        return 100.0 if tasks_completed > 0 else 0.0

    mean = statistics.fmean(rates)
    if mean <= 0:
        return 0.0

    variation = statistics.pstdev(rates) / mean
    return clamp(100.0 - variation * 100.0)


def _deadline_adherence(
    on_time_completed: int,
    completed_with_deadline: int,
    tasks_completed: int,
) -> float:
    if completed_with_deadline > 0:
        return clamp(on_time_completed / completed_with_deadline * 100.0)
    # No deadline-bound tasks this day: do not punish the user for missing data.
    return 100.0 if tasks_completed > 0 else 0.0


def _schedule_adherence(
    blocks_executed: int,
    blocks_scheduled: int,
    tasks_completed: int,
) -> float:
    if blocks_scheduled > 0:
        return clamp(blocks_executed / blocks_scheduled * 100.0)
    # A productive day without time blocks should not be treated as a failure.
    return 100.0 if tasks_completed > 0 else 0.0


def _dominant_factor(
    *,
    weighted_completion: float,
    schedule_adherence: float,
    on_time_ratio: float,
    regularity: float,
    postponement_penalty: float,
) -> tuple[str, list[str]]:
    candidates = [
        (
            "priority-weighted completion",
            weighted_completion,
            COMPLETION_WEIGHT * (weighted_completion - 60.0),
        ),
        (
            "schedule adherence",
            schedule_adherence,
            SCHEDULE_WEIGHT * (schedule_adherence - 60.0),
        ),
        (
            "deadline adherence",
            on_time_ratio,
            ON_TIME_WEIGHT * (on_time_ratio - 60.0),
        ),
        (
            "output regularity",
            regularity,
            REGULARITY_WEIGHT * (regularity - 60.0),
        ),
    ]

    name, value, impact = max(candidates, key=lambda item: abs(item[2]))
    if postponement_penalty > abs(impact) and postponement_penalty > 0:
        dominant = (
            f"Postponements (-{postponement_penalty:.0f} pts) lowered the score."
        )
    elif impact >= 0:
        dominant = f"{name.title()} ({value:.0f}%) lifted the score."
    else:
        dominant = f"{name.title()} ({value:.0f}%) lowered the score."

    insights = [dominant]
    if weighted_completion >= 75:
        insights.append(
            f"High-priority completion stayed strong at {weighted_completion:.0f}%."
        )
    elif weighted_completion < 50:
        insights.append(
            f"Priority-weighted completion fell to {weighted_completion:.0f}%."
        )

    if on_time_ratio < 70:
        insights.append(
            f"Deadline adherence was {on_time_ratio:.0f}%; some tasks finished late."
        )
    if schedule_adherence < 60:
        insights.append(
            f"Only {schedule_adherence:.0f}% of the planned schedule was executed."
        )
    if regularity < 60:
        insights.append(
            f"Erratic daily output reduced the regularity factor to {regularity:.0f}."
        )
    if postponement_penalty > 0:
        insights.append(
            f"Postponements removed {postponement_penalty:.0f} points from the day."
        )

    return dominant, insights[:3]


def compute_daily_score(
    *,
    scheduled_by_priority: Mapping[str, int] | None = None,
    completed_by_priority: Mapping[str, int] | None = None,
    tasks_scheduled: int | None = None,
    tasks_completed: int | None = None,
    on_time_completed: int = 0,
    completed_with_deadline: int = 0,
    blocks_scheduled: int = 0,
    blocks_executed: int = 0,
    postponed_count: int = 0,
    recent_completion_rates: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Score a single day on a 0-100 scale.

    Components:
    - 45% priority-weighted task completion
    - 25% schedule (time-block) adherence
    - 20% deadline adherence
    - 10% output regularity
    - minus a postponement penalty (max 25 points)
    """
    scheduled = dict(scheduled_by_priority or {})
    completed = dict(completed_by_priority or {})

    if not scheduled and tasks_scheduled is not None:
        scheduled = {"medium": max(0, int(tasks_scheduled))}
    if not completed and tasks_completed is not None:
        completed = {"medium": max(0, int(tasks_completed))}

    scheduled_total = sum(max(0, int(count)) for count in scheduled.values())
    completed_total = sum(max(0, int(count)) for count in completed.values())

    weighted_completion = weighted_completion_rate(scheduled, completed)
    on_time_ratio = _deadline_adherence(
        on_time_completed,
        completed_with_deadline,
        completed_total,
    )
    schedule_adherence = _schedule_adherence(
        blocks_executed,
        blocks_scheduled,
        completed_total,
    )
    regularity = _regularity_factor(recent_completion_rates, completed_total)
    postponement_penalty = min(
        MAX_POSTPONEMENT_PENALTY,
        max(0, int(postponed_count)) * POSTPONEMENT_PENALTY_PER_TASK,
    )

    daily_score = clamp(
        COMPLETION_WEIGHT * weighted_completion
        + SCHEDULE_WEIGHT * schedule_adherence
        + ON_TIME_WEIGHT * on_time_ratio
        + REGULARITY_WEIGHT * regularity
        - postponement_penalty
    )

    dominant_factor, insights = _dominant_factor(
        weighted_completion=weighted_completion,
        schedule_adherence=schedule_adherence,
        on_time_ratio=on_time_ratio,
        regularity=regularity,
        postponement_penalty=postponement_penalty,
    )

    return {
        "tasks_scheduled": scheduled_total if tasks_scheduled is None else int(tasks_scheduled),
        "tasks_completed": completed_total if tasks_completed is None else int(tasks_completed),
        "weighted_completion_rate": round(weighted_completion, 2),
        "on_time_ratio": round(on_time_ratio, 2),
        "schedule_adherence": round(schedule_adherence, 2),
        "regularity_factor": round(regularity, 2),
        "postponement_penalty": round(postponement_penalty, 2),
        "daily_score": round(daily_score, 2),
        "dominant_factor": dominant_factor,
        "insights": insights,
    }


def compute_rolling_consistency(
    scores_by_date: Mapping[date | datetime | str, float],
    as_of: date | datetime | str,
    *,
    window_days: int = CONSISTENCY_WINDOW_DAYS,
    decay_lambda: float = DEFAULT_DECAY_LAMBDA,
    missing_score: float | None = None,
) -> float:
    """Exponentially weighted consistency score across a rolling window.

    Recent days receive more weight via ``w_t = exp(-lambda * days_ago)``. When
    ``missing_score`` is ``None``, days without a score are ignored. Otherwise
    the provided value is used for missing calendar days.
    """
    reference = _as_date(as_of)
    normalized = {_as_date(day): float(score) for day, score in scores_by_date.items()}

    weighted_sum = 0.0
    weight_sum = 0.0
    for days_ago in range(max(1, int(window_days))):
        current = reference - timedelta(days=days_ago)
        if current not in normalized and missing_score is None:
            continue
        weight = math.exp(-decay_lambda * days_ago)
        weighted_sum += weight * normalized.get(current, missing_score or 0.0)
        weight_sum += weight

    if weight_sum <= 0:
        return 0.0
    return clamp(weighted_sum / weight_sum)


def compute_streak(active_dates: set[date], as_of: date | datetime | str) -> int:
    """Count consecutive active days ending on ``as_of``."""
    current = _as_date(as_of)
    streak = 0
    while current in active_dates:
        streak += 1
        current -= timedelta(days=1)
    return streak


def heuristic_burnout_risk(
    *,
    workload_intensity: float,
    postponement_rate: float,
    schedule_adherence: float,
    consistency: float,
    completion_trend: float = 0.0,
) -> float:
    """Return a 0-100 burnout/procrastination risk estimate.

    Workload intensity is measured in full workdays (1.0 = 8 hours). A negative
    completion trend (percentage points) raises the risk because a declining
    trajectory is a stronger warning signal than a consistently low one.
    """
    risk = 12.0
    risk += min(32.0, max(0.0, workload_intensity - 0.85) * 40.0)
    risk += min(24.0, max(0.0, postponement_rate) * 50.0)
    risk += max(0.0, 70.0 - schedule_adherence) * 0.28
    risk += max(0.0, 60.0 - consistency) * 0.22
    risk += max(0.0, -completion_trend) * 0.60
    return round(clamp(risk), 2)


def burnout_risk_label(score: float) -> str:
    """Map a numeric risk score to the model's low/moderate/high labels."""
    if score < BURNOUT_LOW_THRESHOLD:
        return "low"
    if score < BURNOUT_HIGH_THRESHOLD:
        return "moderate"
    return "high"


def heuristic_day_archetype(
    *,
    weighted_completion: float,
    workload_intensity: float,
    schedule_adherence: float,
    consistency: float,
) -> str:
    """Fallback day archetype used before the clustering model is available."""
    if workload_intensity >= 1.4 and weighted_completion < 70:
        return OVERLOADED_DRIFT
    if (
        weighted_completion >= 75
        and schedule_adherence >= 60
        and consistency >= 55
    ):
        return DEEP_FOCUS
    if weighted_completion >= 55 or schedule_adherence >= 60:
        return STEADY_FLOW
    return OVERLOADED_DRIFT
