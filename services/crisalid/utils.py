import gc
from typing import Any, Dict

from apps.accounts.models import ProjectUser

from .interface import CrisalidService


def format_crisalid_people(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "external_id": data["uid"],
        "given_name": data["names"][0]["first_names"][0]["value"],
        "family_name": data["names"][0]["last_names"][0]["value"],
    }


def import_crisalid_person(data: Dict[str, Any]) -> ProjectUser:
    person = format_crisalid_people(data)
    external_id = person.pop("external_id")
    user, _ = ProjectUser.objects.update_or_create(
        external_id=external_id, defaults=person
    )
    return user


def import_crisalid_people():
    service = CrisalidService()
    offset = 0
    while offset is not None:
        people, offset = service.people(limit=100, offset=offset)
        people = list(map(format_crisalid_people, people))
        ProjectUser.objects.bulk_create(
            people,
            ignore_conflicts=True,
            update_fields=[],
        )
        gc.collect()
