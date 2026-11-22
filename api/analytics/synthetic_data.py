"""Synthetic multi-persona dataset for training the behavioral models."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd

from . import features, scoring

PERSONAS: dict[str, str] = {
    "consistent_achiever": "Steady high completion with low postponements.",
    "weekend_crammer": "Weak weekdays followed by intense weekend catch-up.",
    "burnout_spiral": "Declining completion, rising workload and postponements.",
    "steady_improver": "Improving completion and schedule adherence over time.",
}

PERSONA_GOAL_BIAS: dict[str, float] = {
    "consistent_achiever": 5.0,
    "weekend_crammer": -3.0,
    "burnout_spiral": -8.0,
    "steady_improver": 1.0,
}

PERSONA_RISK_BIAS: dict[str, float] = {
    "consistent_achiever": -10.0,
    "weekend_crammer": 10.0,
    "burnout_spiral": 26.0,
    "steady_improver": 1.0,
}


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _persona_profile(
    persona: str,
    progress: float,
    is_weekend: bool,
    rng: np.random.Generator,
) -> dict[str, float]:
    """Return the latent behavior profile for one persona-day."""
    if persona == "consistent_achiever":
        return {
            "completion": _clip(0.90 + rng.normal(0, 0.035), 0.55, 0.99),
            "workload_hours": max(2.0, 6.1 + rng.normal(0, 0.6)),
            "schedule": _clip(0.90 + rng.normal(0, 0.035), 0.45, 0.99),
            "postponement_rate": max(0.0, rng.normal(0.05, 0.04)),
            "on_time": _clip(0.93 + rng.normal(0, 0.03), 0.5, 0.99),
            "goal_share": 0.55,
        }

    if persona == "weekend_crammer":
        if is_weekend:
            return {
                "completion": _clip(0.86 + rng.normal(0, 0.05), 0.45, 0.99),
                "workload_hours": max(3.0, 9.0 + rng.normal(0, 1.2)),
                "schedule": _clip(0.84 + rng.normal(0, 0.05), 0.4, 0.99),
                "postponement_rate": max(0.0, rng.normal(0.05, 0.04)),
                "on_time": _clip(0.78 + rng.normal(0, 0.06), 0.35, 0.99),
                "goal_share": 0.4,
            }
        return {
            "completion": _clip(0.38 + rng.normal(0, 0.07), 0.05, 0.8),
            "workload_hours": max(1.0, 3.1 + rng.normal(0, 0.8)),
            "schedule": _clip(0.54 + rng.normal(0, 0.07), 0.15, 0.9),
            "postponement_rate": max(0.0, rng.normal(0.25, 0.08)),
            "on_time": _clip(0.48 + rng.normal(0, 0.08), 0.1, 0.95),
            "goal_share": 0.3,
        }

    if persona == "burnout_spiral":
        return {
            "completion": _clip(0.82 - 0.55 * progress + rng.normal(0, 0.05), 0.05, 0.95),
            "workload_hours": max(2.0, 7.0 + 3.8 * progress + rng.normal(0, 0.8)),
            "schedule": _clip(0.84 - 0.48 * progress + rng.normal(0, 0.06), 0.1, 0.95),
            "postponement_rate": max(0.02, 0.06 + 0.30 * progress + rng.normal(0, 0.05)),
            "on_time": _clip(0.80 - 0.42 * progress + rng.normal(0, 0.07), 0.05, 0.95),
            "goal_share": 0.35,
        }

    # steady_improver
    return {
        "completion": _clip(0.42 + 0.47 * progress + rng.normal(0, 0.05), 0.1, 0.97),
        "workload_hours": max(1.5, 4.2 + 1.4 * progress + rng.normal(0, 0.7)),
        "schedule": _clip(0.52 + 0.35 * progress + rng.normal(0, 0.06), 0.2, 0.95),
        "postponement_rate": max(0.01, 0.22 - 0.16 * progress + rng.normal(0, 0.04)),
        "on_time": _clip(0.58 + 0.30 * progress + rng.normal(0, 0.06), 0.2, 0.97),
        "goal_share": 0.45,
    }


def generate_daily_dataset(
    *,
    users_per_persona: int = 30,
    days: int = 45,
    seed: int = 42,
    start_date: date | None = None,
) -> pd.DataFrame:
    """Generate realistic daily behavior rows for all synthetic personas."""
    if users_per_persona < 1:
        raise ValueError("users_per_persona must be at least 1.")
    if days < 14:
        raise ValueError("days must be at least 14 to produce rolling features.")

    start = start_date or date(2026, 1, 1)
    rows: list[dict[str, Any]] = []
    user_id = 0

    for persona in PERSONAS:
        for _ in range(users_per_persona):
            user_id += 1
            rng = np.random.default_rng(seed + user_id * 7919)

            for day_index in range(days):
                current = start + timedelta(days=day_index)
                is_weekend = current.weekday() >= 5
                progress = day_index / max(1, days - 1)
                profile = _persona_profile(persona, progress, is_weekend, rng)

                scheduled = int(
                    np.clip(
                        rng.integers(5, 12) + (2 if profile["workload_hours"] > 7 else 0),
                        4,
                        16,
                    )
                )
                high_scheduled = max(1, int(round(scheduled * rng.uniform(0.15, 0.28))))
                low_scheduled = int(round(scheduled * rng.uniform(0.20, 0.35)))
                medium_scheduled = max(0, scheduled - high_scheduled - low_scheduled)

                high_completed = int(
                    rng.binomial(
                        high_scheduled,
                        _clip(profile["completion"] + 0.12, 0.0, 0.99),
                    )
                )
                medium_completed = int(
                    rng.binomial(
                        medium_scheduled,
                        _clip(profile["completion"], 0.0, 0.99),
                    )
                )
                low_completed = int(
                    rng.binomial(
                        low_scheduled,
                        _clip(profile["completion"] - 0.12, 0.0, 0.99),
                    )
                )
                tasks_completed = high_completed + medium_completed + low_completed

                postponements = int(
                    np.clip(
                        rng.poisson(profile["postponement_rate"] * scheduled),
                        0,
                        scheduled,
                    )
                )
                blocks_scheduled = max(
                    1,
                    int(round(scheduled * rng.uniform(0.55, 0.85))),
                )
                blocks_executed = int(
                    rng.binomial(
                        blocks_scheduled,
                        _clip(profile["schedule"], 0.0, 0.99),
                    )
                )
                on_time_completed = int(
                    rng.binomial(
                        tasks_completed,
                        _clip(profile["on_time"], 0.0, 0.99),
                    )
                )
                goal_tasks_completed = int(
                    rng.binomial(
                        tasks_completed,
                        _clip(profile["goal_share"], 0.0, 0.99),
                    )
                )

                rows.append(
                    {
                        "user_id": user_id,
                        "persona": persona,
                        "date": current,
                        "tasks_scheduled": scheduled,
                        "tasks_completed": tasks_completed,
                        "high_scheduled": high_scheduled,
                        "medium_scheduled": medium_scheduled,
                        "low_scheduled": low_scheduled,
                        "high_completed": high_completed,
                        "medium_completed": medium_completed,
                        "low_completed": low_completed,
                        "high_priority_delayed": max(
                            0, high_scheduled - high_completed
                        ),
                        "postponements": postponements,
                        "blocks_scheduled": blocks_scheduled,
                        "blocks_executed": blocks_executed,
                        "on_time_completed": on_time_completed,
                        "completed_with_deadline": tasks_completed,
                        "goal_tasks_completed": goal_tasks_completed,
                        "workload_minutes": max(
                            0,
                            int(
                                profile["workload_hours"] * 60
                                + rng.normal(0, 20)
                            ),
                        ),
                    }
                )

    daily = pd.DataFrame(rows)
    scored = features.apply_heuristic_scores(daily)
    featured = features.build_feature_frame(scored)
    return _add_targets(featured, seed=seed)


def _add_targets(feature_df: pd.DataFrame, *, seed: int) -> pd.DataFrame:
    """Derive supervised targets from behavior signals plus persona priors."""
    df = feature_df.copy()
    rng = np.random.default_rng(seed + 104_729)

    completion_signal = (
        0.42 * df["rolling_completion_rate_14"]
        + 0.18 * df["on_time_ratio_14"]
        + 0.15 * df["schedule_adherence_14"]
        + 0.10 * (100.0 - np.clip(df["avg_postponement_rate_14"] * 2.5, 0, 100))
        + 0.10 * np.clip(df["goal_task_velocity_14"] * 25.0, 0, 100)
        + 0.05 * (100.0 - np.clip(df["workload_intensity_14"] * 60.0, 0, 100))
    )
    persona_goal_bias = df["persona"].map(PERSONA_GOAL_BIAS).fillna(0.0)
    goal_probability = np.clip(
        completion_signal
        + persona_goal_bias
        + rng.normal(0, 5.0, size=len(df)),
        5.0,
        98.0,
    )

    risk = (
        28.0 * np.clip((df["workload_intensity_14"] - 0.9) / 0.9, 0, 1)
        + 24.0 * np.clip(df["avg_postponement_rate_14"] / 30.0, 0, 1)
        + 20.0 * np.clip((70.0 - df["schedule_adherence_14"]) / 70.0, 0, 1)
        + 15.0 * np.clip((65.0 - df["rolling_completion_rate_14"]) / 65.0, 0, 1)
        + 13.0 * np.clip(-df["completion_trend_7"] / 25.0, 0, 1)
        + df["persona"].map(PERSONA_RISK_BIAS).fillna(0.0)
        + rng.normal(0, 4.0, size=len(df))
    )
    risk = np.clip(risk, 0.0, 100.0)
    labels = np.array([scoring.burnout_risk_label(value) for value in risk])

    df["goal_completion_probability"] = np.round(goal_probability, 2)
    df["burnout_risk_score"] = np.round(risk, 2)
    df["burnout_risk_label"] = labels
    return df
