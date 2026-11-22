"""Hybrid inference: heuristic scoring first, ML enrichment after cold start."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Any

import joblib
import numpy as np
from django.utils import timezone

from ..models import DailyPerformanceSnapshot
from . import features, scoring, trainer

COLD_START_DAYS = 14
HYBRID_HEURISTIC_WEIGHT = 0.60
HYBRID_ML_WEIGHT = 0.40

CLUSTER_ADJUSTMENTS: dict[str, float] = {
    scoring.DEEP_FOCUS: 4.0,
    scoring.STEADY_FLOW: 0.0,
    scoring.OVERLOADED_DRIFT: -5.0,
}


def _as_date(value: date | datetime | str | None) -> date:
    if value is None:
        return timezone.localdate()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value[:10])
    raise TypeError(f"Unsupported date value: {value!r}")


@lru_cache(maxsize=1)
def load_bundle() -> dict[str, Any] | None:
    """Load the trained artifact bundle once per process."""
    if not trainer.BUNDLE_PATH.exists():
        return None
    try:
        return joblib.load(trainer.BUNDLE_PATH)
    except Exception:
        return None


def clear_bundle_cache() -> None:
    """Clear the cached bundle, useful after retraining in the same process."""
    load_bundle.cache_clear()


def snapshot_history_days(user, as_of: date | None = None) -> int:
    """Count distinct snapshot days inside the current 14-day window."""
    reference = _as_date(as_of)
    start = reference - timedelta(days=COLD_START_DAYS - 1)
    return (
        DailyPerformanceSnapshot.objects.filter(
            user=user,
            date__gte=start,
            date__lte=reference,
        )
        .values("date")
        .distinct()
        .count()
    )


def _heuristic_context(user, as_of: date) -> dict[str, Any]:
    feature_frame = features.build_user_feature_frame(
        user,
        as_of,
        lookback_days=27,
    )
    if feature_frame.empty:
        return {
            "feature_row": {column: 0.0 for column in features.FEATURE_COLUMNS},
            "daily": {},
            "heuristic_goal_probability": 0.0,
        }

    row = feature_frame.sort_values("date").iloc[-1]
    feature_row = features.latest_feature_row(feature_frame)

    daily = {
        "daily_score": float(row.get("daily_score", 0.0) or 0.0),
        "rolling_consistency_score": float(
            row.get("rolling_consistency_score", 0.0) or 0.0
        ),
        "weighted_completion_rate": float(
            row.get("weighted_completion_rate", 0.0) or 0.0
        ),
        "on_time_ratio": float(row.get("on_time_ratio", 0.0) or 0.0),
        "schedule_adherence": float(row.get("schedule_adherence", 0.0) or 0.0),
        "regularity_factor": float(row.get("regularity_factor", 0.0) or 0.0),
        "postponement_penalty": float(row.get("postponement_penalty", 0.0) or 0.0),
        "burnout_risk_score": float(row.get("burnout_risk_score", 0.0) or 0.0),
        "day_archetype": str(
            row.get("heuristic_day_archetype", scoring.STEADY_FLOW)
            or scoring.STEADY_FLOW
        ),
        "dominant_factor": str(row.get("dominant_factor", "") or ""),
        "streak_days": int(row.get("streak_days", 0) or 0),
    }

    heuristic_goal_probability = scoring.clamp(
        0.45 * float(row.get("rolling_completion_rate_14", 0.0) or 0.0)
        + 0.20 * float(row.get("on_time_ratio_14", 0.0) or 0.0)
        + 0.15 * float(row.get("schedule_adherence_14", 0.0) or 0.0)
        + 0.10 * daily["rolling_consistency_score"]
        + 0.10 * min(100.0, float(row.get("goal_task_velocity_14", 0.0) or 0.0) * 25.0)
        - 0.25 * float(row.get("avg_postponement_rate_14", 0.0) or 0.0)
    )

    return {
        "feature_row": feature_row,
        "daily": daily,
        "heuristic_goal_probability": round(heuristic_goal_probability, 2),
    }


def _heuristic_output(
    *,
    history_days: int,
    context: dict[str, Any],
    goal_probability: float,
    model_available: bool,
) -> dict[str, Any]:
    daily = context["daily"]
    hybrid_score = scoring.clamp(
        0.70 * float(daily.get("daily_score", 0.0))
        + 0.30 * float(daily.get("rolling_consistency_score", 0.0))
    )
    risk_score = float(daily.get("burnout_risk_score", 0.0))
    return {
        "mode": "heuristic",
        "cold_start": history_days < COLD_START_DAYS,
        "model_available": model_available,
        "history_days": history_days,
        "heuristic": daily,
        "prediction": {
            "goal_completion_probability": round(goal_probability, 2),
            "goal_completion_source": "heuristic",
            "burnout_risk": scoring.burnout_risk_label(risk_score),
            "burnout_probabilities": None,
            "cluster_label": daily.get("day_archetype"),
            "hybrid_score": round(hybrid_score, 2),
            "dominant_factor": daily.get("dominant_factor", ""),
            "confidence": "cold_start" if history_days < COLD_START_DAYS else "heuristic",
        },
    }


def _ml_prediction(
    bundle: dict[str, Any],
    feature_row: dict[str, float],
) -> dict[str, Any]:
    columns = bundle["feature_columns"]
    x = np.array([[float(feature_row.get(column, 0.0)) for column in columns]])

    goal_probability = scoring.clamp(float(bundle["goal_model"].predict(x)[0]))

    burnout_model = bundle["burnout_model"]
    probabilities = burnout_model.predict_proba(x)[0]
    classes = [str(label) for label in burnout_model.classes_]
    probability_map = {
        label: round(float(probability), 4)
        for label, probability in zip(classes, probabilities)
    }
    burnout_risk = max(probability_map, key=probability_map.get)

    scaled = bundle["cluster_scaler"].transform(x)
    cluster_id = int(bundle["cluster_model"].predict(scaled)[0])
    cluster_label = bundle["cluster_label_map"].get(
        cluster_id,
        str(cluster_id),
    )

    return {
        "goal_completion_probability": round(goal_probability, 2),
        "burnout_risk": burnout_risk,
        "burnout_probabilities": probability_map,
        "cluster_id": cluster_id,
        "cluster_label": cluster_label,
    }


def predict_user(
    user,
    as_of: date | datetime | str | None = None,
) -> dict[str, Any]:
    """Predict performance for a user using the hybrid fallback strategy."""
    reference = _as_date(as_of)
    history_days = snapshot_history_days(user, reference)
    context = _heuristic_context(user, reference)
    heuristic = context["daily"]

    if history_days < COLD_START_DAYS:
        result = _heuristic_output(
            history_days=history_days,
            context=context,
            goal_probability=context["heuristic_goal_probability"],
            model_available=trainer.BUNDLE_PATH.exists(),
        )
        result["as_of"] = reference.isoformat()
        return result

    bundle = load_bundle()
    if bundle is None:
        result = _heuristic_output(
            history_days=history_days,
            context=context,
            goal_probability=context["heuristic_goal_probability"],
            model_available=False,
        )
        result["as_of"] = reference.isoformat()
        return result

    ml = _ml_prediction(bundle, context["feature_row"])
    heuristic_blend = (
        0.65 * float(heuristic.get("daily_score", 0.0))
        + 0.35 * float(heuristic.get("rolling_consistency_score", 0.0))
    )
    cluster_adjustment = CLUSTER_ADJUSTMENTS.get(ml["cluster_label"], 0.0)
    hybrid_score = scoring.clamp(
        HYBRID_HEURISTIC_WEIGHT * heuristic_blend
        + HYBRID_ML_WEIGHT * ml["goal_completion_probability"]
        + cluster_adjustment
    )

    return {
        "mode": "hybrid",
        "cold_start": False,
        "model_available": True,
        "model_version": bundle.get("version"),
        "trained_at": bundle.get("trained_at"),
        "history_days": history_days,
        "as_of": reference.isoformat(),
        "heuristic": heuristic,
        "ml": ml,
        "prediction": {
            "goal_completion_probability": ml["goal_completion_probability"],
            "goal_completion_source": "ml",
            "burnout_risk": ml["burnout_risk"],
            "burnout_probabilities": ml["burnout_probabilities"],
            "cluster_label": ml["cluster_label"],
            "hybrid_score": round(hybrid_score, 2),
            "dominant_factor": heuristic.get("dominant_factor", ""),
            "confidence": (
                "high"
                if float(heuristic.get("rolling_consistency_score", 0.0)) >= 70.0
                else "medium"
            ),
        },
    }
