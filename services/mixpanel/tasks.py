from apps.commons.utils import clear_memory
from projects.celery import app
from services.mixpanel.interface import MixpanelService
from services.mixpanel.models import MixpanelEvent


@app.task(name="services.mixpanel.tasks.get_new_mixpanel_events")
@clear_memory
def get_new_mixpanel_events():
    if MixpanelEvent.objects.count() == 0:
        events = MixpanelService.get_events()
    else:
        last_date = MixpanelEvent.get_latest_date()
        events = MixpanelService.get_events(last_date)
    events = MixpanelEvent.objects.bulk_create(
        [MixpanelEvent(**event) for event in events],
        ignore_conflicts=True,
    )
    projects = {event.project for event in events}
    for project in projects:
        project.set_cached_views()
