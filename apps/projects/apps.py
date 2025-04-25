from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.projects"
    verbose_name = "Projects projects app"

    def ready(self):
        """Register signals once the apps are loaded."""
        import apps.projects.signals  # noqa
