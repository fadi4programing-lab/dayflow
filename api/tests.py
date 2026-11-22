from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from api.analytics import predictor, scoring
from api.analytics.snapshots import recalculate_user_snapshots
from api.models import DailyPerformanceSnapshot, Goal, Task, TimeBlock


class ScoringEngineTests(TestCase):
    def test_priority_weighted_completion_rewards_high_priority(self):
        high_done = scoring.weighted_completion_rate(
            {"high": 1, "medium": 1, "low": 1},
            {"high": 1},
        )
        low_done = scoring.weighted_completion_rate(
            {"high": 1, "medium": 1, "low": 1},
            {"low": 1},
        )

        self.assertGreater(high_done, low_done)
        self.assertAlmostEqual(high_done, 50.0, places=2)
        self.assertAlmostEqual(low_done, 16.67, places=2)

    def test_postponements_reduce_daily_score(self):
        base_kwargs = {
            "scheduled_by_priority": {"high": 2, "medium": 1, "low": 1},
            "completed_by_priority": {"high": 2, "medium": 1, "low": 0},
            "tasks_scheduled": 4,
            "tasks_completed": 3,
            "on_time_completed": 3,
            "completed_with_deadline": 3,
            "blocks_scheduled": 4,
            "blocks_executed": 3,
            "recent_completion_rates": [75, 75, 75, 75],
        }

        baseline = scoring.compute_daily_score(**base_kwargs)
        penalized = scoring.compute_daily_score(
            **base_kwargs,
            postponed_count=3,
        )

        self.assertLess(penalized["daily_score"], baseline["daily_score"])
        self.assertEqual(baseline["postponement_penalty"], 0.0)
        self.assertEqual(penalized["postponement_penalty"], 12.0)
        self.assertTrue(penalized["dominant_factor"])

    def test_output_regularity_penalizes_erratic_days(self):
        kwargs = {
            "scheduled_by_priority": {"high": 1, "medium": 1},
            "completed_by_priority": {"high": 1, "medium": 1},
            "tasks_scheduled": 2,
            "tasks_completed": 2,
            "on_time_completed": 2,
            "completed_with_deadline": 2,
            "blocks_scheduled": 2,
            "blocks_executed": 2,
        }

        steady = scoring.compute_daily_score(
            **kwargs,
            recent_completion_rates=[80, 80, 80, 80],
        )
        erratic = scoring.compute_daily_score(
            **kwargs,
            recent_completion_rates=[20, 100, 20, 100],
        )

        self.assertGreater(
            steady["regularity_factor"],
            erratic["regularity_factor"],
        )

    def test_exponential_decay_weights_recent_days_more(self):
        as_of = date(2026, 1, 14)
        recent_high = scoring.compute_rolling_consistency(
            {as_of: 100.0, as_of - timedelta(days=13): 0.0},
            as_of,
        )
        old_high = scoring.compute_rolling_consistency(
            {as_of: 0.0, as_of - timedelta(days=13): 100.0},
            as_of,
        )

        self.assertGreater(recent_high, old_high)
        self.assertGreater(recent_high, 50.0)
        self.assertLess(old_high, 50.0)


class SignalSnapshotTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            "signal-user",
            "signal@example.com",
            "password",
        )
        self.today = timezone.localdate()

    def test_task_create_update_delete_refreshes_today(self):
        task = Task.objects.create(
            user=self.user,
            title="Signal task",
            priority="high",
            deadline=self.today,
        )
        snapshot = DailyPerformanceSnapshot.objects.get(
            user=self.user,
            date=self.today,
        )
        self.assertEqual(snapshot.tasks_scheduled, 1)
        self.assertEqual(snapshot.tasks_completed, 0)

        task.is_completed = True
        task.save()
        snapshot.refresh_from_db()
        self.assertEqual(snapshot.tasks_completed, 1)
        self.assertGreater(snapshot.daily_score, 0)

        task.delete()
        self.assertFalse(
            DailyPerformanceSnapshot.objects.filter(
                user=self.user,
                date=self.today,
            ).exists()
        )

    def test_timeblock_execution_updates_schedule_adherence(self):
        block = TimeBlock.objects.create(
            user=self.user,
            title="Signal block",
            date=self.today,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        snapshot = DailyPerformanceSnapshot.objects.get(
            user=self.user,
            date=self.today,
        )
        self.assertEqual(snapshot.schedule_adherence, 0.0)

        block.is_executed = True
        block.save()
        snapshot.refresh_from_db()
        self.assertEqual(snapshot.schedule_adherence, 100.0)

        block.delete()
        self.assertFalse(
            DailyPerformanceSnapshot.objects.filter(
                user=self.user,
                date=self.today,
            ).exists()
        )


class PredictionPipelineTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()

    def _user(self, username: str) -> User:
        return User.objects.create_user(
            username,
            f"{username}@example.com",
            "password",
        )

    def test_cold_start_uses_heuristic_engine(self):
        user = self._user("cold-user")

        result = predictor.predict_user(user, self.today)

        self.assertEqual(result["mode"], "heuristic")
        self.assertTrue(result["cold_start"])
        self.assertEqual(result["history_days"], 0)
        self.assertIn(
            result["prediction"]["burnout_risk"],
            {"low", "moderate", "high"},
        )

    def test_fewer_than_fourteen_snapshot_days_stays_cold(self):
        user = self._user("short-user")
        for offset in range(5):
            DailyPerformanceSnapshot.objects.create(
                user=user,
                date=self.today - timedelta(days=offset),
                daily_score=70.0,
            )

        result = predictor.predict_user(user, self.today)

        self.assertEqual(result["mode"], "heuristic")
        self.assertTrue(result["cold_start"])
        self.assertEqual(result["history_days"], 5)

    def test_fourteen_snapshot_days_switch_to_hybrid(self):
        user = self._user("warm-user")
        for offset in range(14):
            day = self.today - timedelta(days=offset)
            Task.objects.create(
                user=user,
                title=f"Warm task {offset}",
                priority="high",
                deadline=day,
                estimated_minutes=45,
                is_completed=True,
                completed_at=timezone.now() - timedelta(days=offset),
            )

        result_counts = recalculate_user_snapshots(
            user,
            days=14,
            end_date=self.today,
        )
        self.assertGreaterEqual(result_counts["snapshots"], 14)

        bundle = predictor.load_bundle()
        self.assertIsNotNone(bundle, "Train the AI engine before running tests.")

        result = predictor.predict_user(user, self.today)

        self.assertEqual(result["mode"], "hybrid")
        self.assertFalse(result["cold_start"])
        self.assertGreaterEqual(result["history_days"], 14)
        self.assertIn("ml", result)
        self.assertIn(
            result["ml"]["cluster_label"],
            {"Deep Focus", "Steady Flow", "Overloaded / Drift"},
        )
        self.assertIn(
            result["prediction"]["burnout_risk"],
            {"low", "moderate", "high"},
        )
        self.assertGreaterEqual(
            result["prediction"]["goal_completion_probability"],
            0,
        )
        self.assertLessEqual(
            result["prediction"]["goal_completion_probability"],
            100,
        )


class AnalyticsApiTests(TestCase):
    def setUp(self):
        self.today = timezone.localdate()
        self.user = User.objects.create_user(
            "analytics-user",
            "analytics@example.com",
            "password",
        )
        self.other = User.objects.create_user(
            "other-user",
            "other@example.com",
            "password",
        )
        self.goal = Goal.objects.create(
            user=self.user,
            title="Ship analytics",
            progress=40,
            target_date=self.today + timedelta(days=7),
        )
        self.other_goal = Goal.objects.create(
            user=self.other,
            title="Other goal",
            progress=90,
        )
        Task.objects.create(
            user=self.user,
            title="Analytics task",
            priority="high",
            deadline=self.today,
            is_completed=True,
        )

    def _client(self, user) -> APIClient:
        refresh = RefreshToken.for_user(user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        return client

    def test_overview_requires_authentication(self):
        response = APIClient().get("/api/analytics/overview/")
        self.assertIn(response.status_code, (401, 403))

    def test_goals_forecast_requires_authentication(self):
        response = APIClient().get("/api/analytics/goals-forecast/")
        self.assertIn(response.status_code, (401, 403))

    def test_overview_returns_metrics_recommendations_and_series(self):
        response = self._client(self.user).get("/api/analytics/overview/")

        self.assertEqual(response.status_code, 200)
        payload = response.data
        for key in (
            "as_of",
            "mode",
            "cold_start",
            "history_days",
            "recommendations",
            "daily_scores_7d",
            "daily_scores_14d",
        ):
            self.assertIn(key, payload)

        for key in (
            "rolling_consistency_score",
            "daily_score",
            "streak_days",
            "burnout_risk",
            "day_archetype",
            "dominant_factor",
        ):
            self.assertIn(key, payload)

        self.assertTrue(payload["recommendations"])
        self.assertLessEqual(len(payload["daily_scores_7d"]), 7)
        self.assertLessEqual(len(payload["daily_scores_14d"]), 14)
        self.assertGreaterEqual(payload["history_days"], 1)

    def test_overview_is_data_isolated(self):
        own_response = self._client(self.user).get("/api/analytics/overview/")
        other_response = self._client(self.other).get("/api/analytics/overview/")

        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(other_response.status_code, 200)
        self.assertGreaterEqual(own_response.data["history_days"], 1)
        self.assertEqual(other_response.data["history_days"], 0)

    def test_goals_forecast_is_data_isolated(self):
        own_response = self._client(self.user).get(
            "/api/analytics/goals-forecast/"
        )
        other_response = self._client(self.other).get(
            "/api/analytics/goals-forecast/"
        )

        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(other_response.status_code, 200)

        own_titles = [goal["title"] for goal in own_response.data["goals"]]
        other_titles = [goal["title"] for goal in other_response.data["goals"]]

        self.assertEqual(own_titles, ["Ship analytics"])
        self.assertEqual(other_titles, ["Other goal"])

        goal = own_response.data["goals"][0]
        self.assertIn(goal["risk_status"], {"low", "moderate", "high"})
        self.assertGreaterEqual(goal["completion_probability"], 0)
        self.assertLessEqual(goal["completion_probability"], 100)

    def test_recalculate_returns_updated_metrics(self):
        response = self._client(self.user).post("/api/analytics/recalculate/")

        self.assertEqual(response.status_code, 200)
        for key in ("detail", "created", "updated", "skipped", "snapshots", "metrics"):
            self.assertIn(key, response.data)
        self.assertGreaterEqual(response.data["snapshots"], 1)

    def test_jwt_token_endpoint_issues_access_token(self):
        response = APIClient().post(
            "/api/token/",
            {"username": "analytics-user", "password": "password"},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)


class OpenApiTests(TestCase):
    def test_schema_and_swagger_docs_are_available(self):
        schema = APIClient().get("/api/schema/")
        docs = APIClient().get("/api/docs/")

        self.assertEqual(schema.status_code, 200)
        self.assertEqual(docs.status_code, 200)
