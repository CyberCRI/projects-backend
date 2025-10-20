import datetime

from apps.commons.utils import clear_memory
from projects.celery import app
from services.mixpanel.interface import MixpanelService
from services.mixpanel.models import MixpanelEvent


@app.task(name="services.mixpanel.tasks.get_new_mixpanel_events")
@clear_memory
def get_new_mixpanel_events():
    if MixpanelEvent.objects.count() == 0:
        date = MixpanelService.initial_date
    else:
        date = MixpanelEvent.get_latest_date()
    while date <= datetime.date.today():
        events = MixpanelService.get_events(date, date)
        events = MixpanelEvent.objects.bulk_create(
            [MixpanelEvent(**event) for event in events],
            ignore_conflicts=True,
            batch_size=1000,
        )
        date += datetime.timedelta(days=1)
    projects = {event.project for event in events}
    for project in projects:
        project.set_cached_views()
