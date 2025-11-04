import datetime
import json
from typing import Optional

from apps.organizations.models import Organization
from apps.projects.models import Project
from django.conf import settings
from django.db.models import Q
from mixpanel_utils import MixpanelUtils


class MixpanelService:
    """
    Service to fetch Mixpanel events and store them in the database.
    """

    initial_date = datetime.date(2021, 9, 1)
    service = MixpanelUtils(
        api_secret=settings.MIXPANEL_API_SECRET,
        project_id=settings.MIXPANEL_PROJECT_ID,
        residency="eu",
    )

    @classmethod
    def response_to_json(cls, response: str) -> list:
        """
        Mixpanel returns a string with a list of events, but it's not a valid JSON.
        This method converts the string to a valid JSON.
        """
        events = f"[{response[:-1]}]".replace("\n", ",")
        return json.loads(events)

    @classmethod
    def format_event(cls, event: dict) -> dict:
        """
        Format the event to be stored in the database.
        """
        properties = event["properties"]

        project_id = properties["project"]["id"]
        project = Project.objects.all_with_delete().filter(
            Q(id=project_id) | Q(slug=project_id)
        )
        organization_code = properties.get("organization", {}).get("code", "_")
        organization = Organization.objects.filter(code=organization_code)

        return {
            "mixpanel_id": properties["$insert_id"],
            "date": datetime.date.fromtimestamp(properties["time"]),
            "project": project.get() if project.exists() else None,
            "organization": organization.get() if organization.exists() else None,
        }

    @classmethod
    def get_events(
        cls,
        from_date: datetime.date = initial_date,
        to_date: datetime.date | None = None,
        event: str = "page_viewed",
    ) -> list:
        """
        Get the events from Mixpanel and format them to be stored in the database.
        """
        to_date = to_date or datetime.date.today()
        response = cls.service.request(
            cls.service.raw_api,
            ["export"],
            {
                "from_date": from_date.isoformat(),
                "to_date": to_date.isoformat(),
                "event": [event],
            },
            headers={},
            raw_stream=False,
        )
        if response is not None:
            events = cls.response_to_json(response)
            formated_events = [
                cls.format_event(event)
                for event in events
                if event.get("properties", {}).get("project", {}).get("id", None)
            ]
            return list(filter(lambda e: e["project"], formated_events))
        return []
