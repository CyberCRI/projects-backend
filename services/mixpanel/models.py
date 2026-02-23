import datetime

from django.db import models

from apps.organizations.models import Organization
from apps.projects.models import Project


class MixpanelEvent(models.Model):
    date = models.DateField()
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="mixpanel_events"
    )
    organization = models.ForeignKey(Organization, null=True, on_delete=models.CASCADE)
    mixpanel_id = models.CharField(max_length=255, unique=True)

    @classmethod
    def get_latest_date(cls) -> datetime.date:
        return cls.objects.latest("date").date

    class Meta:
        ordering = ["-date"]
