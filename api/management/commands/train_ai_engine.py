"""Train the hybrid behavioral models and write artifacts."""

import json

from django.core.management.base import BaseCommand

from api.analytics import trainer


class Command(BaseCommand):
    help = "Generate synthetic data, train the behavioral models, and save artifacts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--users-per-persona",
            type=int,
            default=30,
            help="Synthetic users generated for each persona (default: 30).",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=45,
            help="Days of history generated per synthetic user (default: 45).",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducible training (default: 42).",
        )

    def handle(self, *args, **options):
        metrics = trainer.train_bundle(
            users_per_persona=options["users_per_persona"],
            days=options["days"],
            seed=options["seed"],
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Saved model bundle to {trainer.BUNDLE_PATH}"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(f"Saved metrics to {trainer.METRICS_PATH}")
        )
        self.stdout.write("")
        self.stdout.write("Evaluation metrics:")
        self.stdout.write(
            json.dumps(
                {
                    "dataset": metrics["dataset"],
                    "goal_completion": metrics["goal_completion"],
                    "burnout_risk": metrics["burnout_risk"],
                    "clustering": metrics["clustering"],
                },
                indent=2,
            )
        )
