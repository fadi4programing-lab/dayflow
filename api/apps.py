from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'

    def ready(self):
        import sys
        # Don't run scheduler during migrations or tests
        if 'migrate' in sys.argv or 'makemigrations' in sys.argv:
            return
        try:
            from .scheduler import start
            start()
        except Exception as e:
            print(f"[dayflow] Scheduler failed to start: {e}")