"""JWT-protected analytics REST endpoints."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from django.db.models import Count, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ..models import Goal, Task
from . import features, predictor, scoring
from .serializers import (
    AnalyticsOverviewSerializer,
    GoalsForecastResponseSerializer,
    RecalculateResponseSerializer,
)
from .snapshots import recalculate_user_snapshots

METRIC_FIELDS = (
    "rolling_consistency_score",
    "daily_score",
    "streak_days",
    "burnout_risk",
    "day_archetype",
    "dominant_factor",
    "weighted_completion_rate",
    "schedule_adherence",
    "goal_completion_probability",
    "hybrid_score",
    "mode",
)


def _as_date(value: date | datetime) -> date:
    if isinstance(value, datetime):
        return value.date()
    return value


def _daily_series(user, as_of: date, days: int = 14) -> list[dict[str, Any]]:
    start = as_of - timedelta(days=days - 1)
    daily = features.build_daily_frame(user, start, as_of)
    if daily.empty:
        return []

    points: list[dict[str, Any]] = []
    for _, row in daily.sort_values("date").iterrows():
        points.append(
            {
                "date": _as_date(row["date"]),
                "score": round(float(row.get("daily_score", 0.0) or 0.0), 2),
            }
        )
    return points


def _recommendations(
    metrics: dict[str, Any],
    *,
    mode: str,
) -> list[str]:
    recommendations: list[str] = []

    if metrics.get("burnout_risk") == "high":
        recommendations.append(
            "Lower today's planned workload and protect a recovery block."
        )
    elif metrics.get("burnout_risk") == "moderate":
        recommendations.append(
            "Keep the workload moderate and avoid stacking high-priority tasks."
        )

    if float(metrics.get("schedule_adherence", 0.0)) < 60.0:
        recommendations.append(
            "Turn the next priority into a concrete time block and execute it."
        )

    if float(metrics.get("rolling_consistency_score", 0.0)) < 50.0:
        recommendations.append(
            "Aim for a small, repeatable daily target instead of occasional bursts."
        )

    if float(metrics.get("daily_score", 0.0)) < 60.0:
        recommendations.append(
            "Start with one high-priority task to rebuild momentum."
        )

    if int(metrics.get("streak_days", 0)) >= 3:
        recommendations.append(
            "Protect your active streak with at least 15 minutes of focused work."
        )

    if not recommendations:
        recommendations.append(
            "The current cadence is steady; review goal deadlines weekly."
        )

    if mode == "heuristic":
        recommendations.append(
            "Keep logging daily activity to unlock the ML-backed forecast."
        )

    return recommendations[:4]


def _build_overview(user, as_of: date | None = None) -> dict[str, Any]:
    reference = as_of or timezone.localdate()
    prediction = predictor.predict_user(user, reference)
    heuristic = prediction.get("heuristic", {})
    outcome = prediction.get("prediction", {})

    metrics = {
        "rolling_consistency_score": round(
            float(heuristic.get("rolling_consistency_score", 0.0) or 0.0), 2
        ),
        "daily_score": round(
            float(heuristic.get("daily_score", 0.0) or 0.0), 2
        ),
        "streak_days": int(heuristic.get("streak_days", 0) or 0),
        "burnout_risk": str(outcome.get("burnout_risk", "low")),
        "day_archetype": str(
            outcome.get("cluster_label")
            or heuristic.get("day_archetype")
            or scoring.STEADY_FLOW
        ),
        "dominant_factor": str(
            outcome.get("dominant_factor")
            or heuristic.get("dominant_factor")
            or ""
        ),
        "weighted_completion_rate": round(
            float(heuristic.get("weighted_completion_rate", 0.0) or 0.0), 2
        ),
        "schedule_adherence": round(
            float(heuristic.get("schedule_adherence", 0.0) or 0.0), 2
        ),
        "goal_completion_probability": outcome.get("goal_completion_probability"),
        "hybrid_score": outcome.get("hybrid_score"),
        "mode": prediction.get("mode"),
    }

    series = _daily_series(user, reference, days=14)
    return {
        "as_of": reference,
        **metrics,
        "cold_start": bool(prediction.get("cold_start")),
        "history_days": int(prediction.get("history_days", 0) or 0),
        "recommendations": _recommendations(
            metrics,
            mode=str(prediction.get("mode", "heuristic")),
        ),
        "daily_scores_7d": series[-7:],
        "daily_scores_14d": series[-14:],
    }


def _goal_risk_status(
    goal: Goal,
    *,
    burnout_risk: str,
    progress: int,
    as_of: date,
) -> str:
    if goal.target_date and goal.target_date < as_of:
        return "high"
    if burnout_risk == "high":
        return "high"
    if burnout_risk == "moderate" or progress < 35:
        return "moderate"
    return "low"


def _goal_forecasts(user, as_of: date) -> dict[str, Any]:
    prediction = predictor.predict_user(user, as_of)
    outcome = prediction.get("prediction", {})
    base_probability = float(
        outcome.get("goal_completion_probability", 0.0) or 0.0
    )
    burnout_risk = str(outcome.get("burnout_risk", "low"))

    goals = list(
        Goal.objects.filter(user=user, is_completed=False).order_by(
            "target_date", "id"
        )
    )
    goal_ids = [goal.pk for goal in goals]
    stats = {
        row["goal_id"]: row
        for row in Task.objects.filter(
            user=user,
            goal_id__in=goal_ids,
        )
        .values("goal_id")
        .annotate(
            total=Count("id"),
            completed=Count("id", filter=Q(is_completed=True)),
        )
    }

    forecasts: list[dict[str, Any]] = []
    for goal in goals:
        counts = stats.get(goal.pk, {"total": 0, "completed": 0})
        total = int(counts["total"])
        completed = int(counts["completed"])

        progress = int(goal.progress or 0)
        if total == 0:
            factor = "No linked tasks yet; add tasks to sharpen the forecast."
        elif completed == total:
            progress = 100
            factor = "All linked tasks are complete; protect the finish line."
        else:
            progress = round(completed / total * 100)
            if progress < 40:
                factor = "Low linked-task completion is the main drag."
            else:
                factor = "Linked-task completion is supporting the forecast."

        completion_probability = scoring.clamp(
            0.60 * base_probability + 0.40 * progress
        )
        forecasts.append(
            {
                "id": goal.pk,
                "title": goal.title,
                "progress": progress,
                "target_date": goal.target_date,
                "tasks_total": total,
                "tasks_completed": completed,
                "completion_probability": round(completion_probability, 2),
                "risk_status": _goal_risk_status(
                    goal,
                    burnout_risk=burnout_risk,
                    progress=progress,
                    as_of=as_of,
                ),
                "dominant_factor": factor,
            }
        )

    return {
        "as_of": as_of,
        "mode": prediction.get("mode"),
        "goals": forecasts,
    }


@extend_schema(
    tags=["Analytics"],
    responses={200: AnalyticsOverviewSerializer},
    description="Daily behavioral metrics, recommendations, and score history.",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def overview(request):
    as_of = timezone.localdate()
    return Response(_build_overview(request.user, as_of))


@extend_schema(
    tags=["Analytics"],
    responses={200: GoalsForecastResponseSerializer},
    description="Active goals with ML-assisted completion probability and risk.",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def goals_forecast(request):
    as_of = timezone.localdate()
    return Response(_goal_forecasts(request.user, as_of))


@extend_schema(
    tags=["Analytics"],
    request=None,
    responses={200: RecalculateResponseSerializer},
    description="Rebuild the authenticated user's recent snapshots and metrics.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def recalculate(request):
    as_of = timezone.localdate()
    result = recalculate_user_snapshots(
        request.user,
        days=None,
        end_date=as_of,
    )
    overview_data = _build_overview(request.user, as_of)
    return Response(
        {
            "detail": "Snapshots recalculated.",
            "created": result["created"],
            "updated": result["updated"],
            "skipped": result["skipped"],
            "snapshots": result["snapshots"],
            "metrics": {
                field: overview_data.get(field) for field in METRIC_FIELDS
            },
        }
    )
