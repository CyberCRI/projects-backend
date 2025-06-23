import gc
from typing import Any, Dict

from django.contrib.contenttypes.models import ContentType

from apps.accounts.models import ProjectUser

from .models import CrisalidId, ResearchDocument, Researcher, ResearchInstitution, ResearchTeam
from .interface import CrisalidService


def format_crisalid_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": data["uid"],
        "given_name": data["names"][0]["first_names"][0]["value"],
        "family_name": data["names"][0]["last_names"][0]["value"],
    }


def import_crisalid_profile(data: Dict[str, Any]) -> Researcher:
    data = format_crisalid_profile(data)
    crisalid_id, created = CrisalidId.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(Researcher),
        id_type=CrisalidId.IDType.CRISALID,
        value=data["id"],
    )
    if created:
        user = ProjectUser.objects.create(
            given_name=data["given_name"],
            family_name=data["family_name"],
            email="fake@example.com",
            external_id=data["id"],
        )
        researcher = Researcher.objects.create(user=user)
        researcher.crisalid_ids.add(crisalid_id)
        return researcher
    return Researcher.objects.get(crisalid_ids=crisalid_id)


def import_crisalid_profiles():
    service = CrisalidService()
    offset = 0
    while offset is not None:
        profiles, offset = service.profiles(limit=100, offset=offset)
        for profile in profiles:
            import_crisalid_profile(profile)
        gc.collect()  # Clean up memory after processing each batch

