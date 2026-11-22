"""Populate DailyPerformanceSnapshot rows from raw behavioral records."""

from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from api.analytics import features, scoring
from api.models import DailyPerformanceSnapshot


class Command(BaseCommand):
    help = "Compute daily behavioral snapshots for one user or all users."

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Number of recent days to store (default: 30).",
        )
        parser.add_argument(
            "--user-id",
            type=int,
            help="Only compute snapshots for this user id.",
        )

    def handle(self, *args, **options):
        days = max(1, int(options["days"]))
        end = timezone.localdate()
        start = end - timedelta(days=days - 1)
        history_start = start - timedelta(
            days=scoring.CONSISTENCY_WINDOW_DAYS + 1
        )

        users = User.objects.all().order_by("pk")
        if options.get("user_id"):
            users = users.filter(pk=options["user_id"])
            if not users.exists():
                raise CommandError(f"User {options['user_id']} does not exist.")

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for user in users:
            daily = features.build_daily_frame(user, history_start, end)
            if daily.empty:
                continue

            window = daily[
                (daily["date"] >= start) & (daily["date"] <= end)
            ]
            for _, row in window.iterrows():
                tasks_scheduled = int(row.get("tasks_scheduled", 0) or 0)
                tasks_completed = int(row.get("tasks_completed", 0) or 0)
                blocks_scheduled = int(row.get("blocks_scheduled", 0) or 0)

                # Empty days should not manufacture snapshot history: a new
                # user must remain in cold-start mode until real activity exists.
                if tasks_scheduled == 0 and tasks_completed == 0 and blocks_scheduled == 0:
                    skipped_count += 1
                    continue

                day = row["date"]
                if isinstance(day, datetime):
                    day = day.date()

                _, created = DailyPerformanceSnapshot.objects.update_or_create(
                    user=user,
                    date=day,
                    defaults={
                        "tasks_scheduled": tasks_scheduled,
                        "tasks_completed": tasks_completed,
                        "weighted_completion_rate": float(
                            row.get("weighted_completion_rate", 0.0) or 0.0
                        ),
                        "on_time_ratio": float(row.get("on_time_ratio", 0.0) or 0.0),
                        "schedule_adherence": float(
                            row.get("schedule_adherence", 0.0) or 0.0
                        ),
                        "daily_score": float(row.get("daily_score", 0.0) or 0.0),
                        "rolling_consistency_score": float(
                            row.get("rolling_consistency_score", 0.0) or 0.0
                        ),
                        "streak_days": int(row.get("streak_days", 0) or 0),
                        "burnout_risk": float(
                            row.get("burnout_risk_score", 0.0) or 0.0
                        ),
                        "day_archetype": str(
                            row.get("heuristic_day_archetype", "") or ""
                        ),
                        "dominant_factor": str(row.get("dominant_factor", "") or ""),
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                "Snapshots computed: "
                f"{created_count} created, {updated_count} updated, "
                f"{skipped_count} empty days skipped."
            )
        )
