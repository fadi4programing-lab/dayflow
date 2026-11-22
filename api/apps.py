from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        import sys

        # Connect behavioral snapshot signals for every runtime path.
        from . import signals  # noqa: F401

        # Don't run the background scheduler for one-off management commands.
        skip_scheduler_commands = {
            'migrate',
            'makemigrations',
            'test',
            'check',
            'train_ai_engine',
            'compute_snapshots',
            'spectacular',
            'collectstatic',
        }
        if len(sys.argv) > 1 and sys.argv[1] in skip_scheduler_commands:
            return
        try:
            from .scheduler import start
            start()
        except Exception as e:
            print(f"[dayflow] Scheduler failed to start: {e}")