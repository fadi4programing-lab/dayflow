"""Populate DailyPerformanceSnapshot rows from raw behavioral records."""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from api.analytics.snapshots import recalculate_user_snapshots


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

        users = User.objects.all().order_by("pk")
        if options.get("user_id"):
            users = users.filter(pk=options["user_id"])
            if not users.exists():
                raise CommandError(f"User {options['user_id']} does not exist.")

        created_count = 0
        updated_count = 0
        skipped_count = 0
        snapshot_count = 0

        for user in users:
            result = recalculate_user_snapshots(
                user,
                days=days,
                end_date=end,
            )
            created_count += result["created"]
            updated_count += result["updated"]
            skipped_count += result["skipped"]
            snapshot_count += result["snapshots"]

        self.stdout.write(
            self.style.SUCCESS(
                "Snapshots computed: "
                f"{created_count} created, {updated_count} updated, "
                f"{skipped_count} empty days skipped, "
                f"{snapshot_count} snapshots in the window."
            )
        )
