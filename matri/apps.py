# matri/apps.py

from django.apps import AppConfig


class MatriConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'matri'

    def ready(self):
        """
        This method is called when the app is ready.
        It's the correct place to import signals.
        """
        import matri.signals  # This line is the only addition needed.