"""Training pipeline for the hybrid behavioral models."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.cluster import KMeans
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    mean_absolute_error,
    r2_score,
    roc_auc_score,
    silhouette_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from . import features, scoring, synthetic_data

ARTIFACTS_DIR = Path(__file__).resolve().parent / "artifacts"
BUNDLE_PATH = ARTIFACTS_DIR / "consistency_bundle.joblib"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"
MODEL_VERSION = "1.0.0"
RANDOM_STATE = 42
CLUSTER_LABELS = [
    scoring.DEEP_FOCUS,
    scoring.STEADY_FLOW,
    scoring.OVERLOADED_DRIFT,
]


def _split_by_user(
    data: pd.DataFrame,
    *,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Hold out entire users so adjacent days cannot leak across the split."""
    rng = np.random.default_rng(seed)
    test_users: list[int] = []

    for _, persona_rows in data.groupby("persona"):
        users = np.array(sorted(persona_rows["user_id"].unique()))
        rng.shuffle(users)
        holdout = max(1, int(round(len(users) * 0.25)))
        test_users.extend(int(user) for user in users[:holdout])

    train = data[~data["user_id"].isin(test_users)].copy()
    test = data[data["user_id"].isin(test_users)].copy()

    # A rare persona distribution can leave a class out of the holdout. Fall
    # back to a stratified row split so the evaluation remains meaningful.
    if set(test["burnout_risk_label"].unique()) != set(
        data["burnout_risk_label"].unique()
    ):
        train, test = train_test_split(
            data,
            test_size=0.2,
            random_state=seed,
            stratify=data["burnout_risk_label"],
        )
        train = train.copy()
        test = test.copy()

    return train, test


def _cluster_label_map(
    kmeans: KMeans,
    scaler: StandardScaler,
) -> dict[int, str]:
    """Map arbitrary KMeans ids to human-readable work-pattern labels."""
    centers = scaler.inverse_transform(kmeans.cluster_centers_)
    feature_index = {name: index for index, name in enumerate(features.FEATURE_COLUMNS)}
    scored_centers: list[tuple[int, float]] = []

    for cluster_id, center in enumerate(centers):
        completion = center[feature_index["rolling_completion_rate_7"]]
        schedule = center[feature_index["schedule_adherence_7"]]
        postponement = center[feature_index["avg_postponement_rate_7"]]
        workload = center[feature_index["workload_intensity_7"]]
        quality = (
            completion * 0.50
            + schedule * 0.25
            - postponement * 0.15
            - max(0.0, workload - 1.0) * 25.0
        )
        scored_centers.append((int(cluster_id), float(quality)))

    ordered = sorted(scored_centers, key=lambda item: item[1], reverse=True)
    return {
        cluster_id: CLUSTER_LABELS[position]
        for position, (cluster_id, _) in enumerate(ordered)
    }


def _top_importances(model: RandomForestClassifier) -> list[dict[str, Any]]:
    importances = zip(features.FEATURE_COLUMNS, model.feature_importances_)
    ordered = sorted(importances, key=lambda item: item[1], reverse=True)[:10]
    return [
        {"feature": name, "importance": round(float(value), 4)}
        for name, value in ordered
    ]


def train_bundle(
    *,
    users_per_persona: int = 30,
    days: int = 45,
    seed: int = RANDOM_STATE,
) -> dict[str, Any]:
    """Generate synthetic data, train all artifacts, and persist the bundle."""
    data = synthetic_data.generate_daily_dataset(
        users_per_persona=users_per_persona,
        days=days,
        seed=seed,
    )
    train, test = _split_by_user(data, seed=seed)

    x_train = train[features.FEATURE_COLUMNS].to_numpy(dtype=float)
    x_test = test[features.FEATURE_COLUMNS].to_numpy(dtype=float)

    goal_model = GradientBoostingRegressor(
        n_estimators=250,
        learning_rate=0.05,
        max_depth=3,
        random_state=seed,
        loss="squared_error",
    )
    goal_model.fit(x_train, train["goal_completion_probability"].to_numpy(dtype=float))
    goal_predictions = goal_model.predict(x_test)
    goal_metrics = {
        "model": "GradientBoostingRegressor",
        "mae": round(float(mean_absolute_error(test["goal_completion_probability"], goal_predictions)), 4),
        "r2": round(float(r2_score(test["goal_completion_probability"], goal_predictions)), 4),
    }

    burnout_model = RandomForestClassifier(
        n_estimators=350,
        max_depth=10,
        min_samples_leaf=3,
        class_weight="balanced_subsample",
        random_state=seed,
        n_jobs=-1,
    )
    burnout_model.fit(x_train, train["burnout_risk_label"])
    burnout_predictions = burnout_model.predict(x_test)
    burnout_probabilities = burnout_model.predict_proba(x_test)
    burnout_metrics = {
        "model": "RandomForestClassifier",
        "accuracy": round(float(accuracy_score(test["burnout_risk_label"], burnout_predictions)), 4),
        "roc_auc_weighted_ovr": round(
            float(
                roc_auc_score(
                    test["burnout_risk_label"],
                    burnout_probabilities,
                    multi_class="ovr",
                    average="weighted",
                    labels=burnout_model.classes_,
                )
            ),
            4,
        ),
        "classes": [str(label) for label in burnout_model.classes_],
    }

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)
    x_test_scaled = scaler.transform(x_test)

    cluster_model = KMeans(
        n_clusters=len(CLUSTER_LABELS),
        n_init=10,
        random_state=seed,
    )
    cluster_model.fit(x_train_scaled)
    test_clusters = cluster_model.predict(x_test_scaled)
    silhouette = silhouette_score(x_test_scaled, test_clusters)
    cluster_label_map = _cluster_label_map(cluster_model, scaler)
    cluster_metrics = {
        "model": "KMeans",
        "n_clusters": len(CLUSTER_LABELS),
        "silhouette_score": round(float(silhouette), 4),
        "label_map": {
            str(cluster_id): label
            for cluster_id, label in cluster_label_map.items()
        },
        "test_cluster_distribution": {
            label: int(count)
            for label, count in pd.Series(
                [cluster_label_map[int(cluster)] for cluster in test_clusters]
            ).value_counts().items()
        },
    }

    trained_at = datetime.now(timezone.utc).isoformat()
    metrics: dict[str, Any] = {
        "model_version": MODEL_VERSION,
        "trained_at": trained_at,
        "environment": {
            "scikit_learn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "dataset": {
            "rows": int(len(data)),
            "users": int(data["user_id"].nunique()),
            "days_per_user": int(days),
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
            "personas": {
                name: int(count)
                for name, count in data["persona"].value_counts().items()
            },
            "burnout_labels": {
                name: int(count)
                for name, count in data["burnout_risk_label"].value_counts().items()
            },
        },
        "goal_completion": goal_metrics,
        "burnout_risk": burnout_metrics,
        "clustering": cluster_metrics,
        "feature_columns": features.FEATURE_COLUMNS,
    }
    metrics["top_feature_importances"] = _top_importances(burnout_model)

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    bundle = {
        "version": MODEL_VERSION,
        "trained_at": trained_at,
        "sklearn_version": sklearn.__version__,
        "feature_columns": features.FEATURE_COLUMNS,
        "goal_model": goal_model,
        "burnout_model": burnout_model,
        "cluster_model": cluster_model,
        "cluster_scaler": scaler,
        "cluster_label_map": cluster_label_map,
        "burnout_classes": [str(label) for label in burnout_model.classes_],
        "metrics": metrics,
    }
    joblib.dump(bundle, BUNDLE_PATH, compress=3)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    return metrics
