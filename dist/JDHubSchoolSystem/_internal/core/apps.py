from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'OfficeHub Core'

    def ready(self):
        # Import signal handlers so they are registered when the app is ready
        try:
            from . import signals  # noqa: F401
        except Exception:
            pass
