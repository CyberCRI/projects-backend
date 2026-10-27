import datetime
import logging

from django.conf import settings

from apps.organizations.models import Organization
from projects.celery import app
from services.crisalid.bus.constant import CrisalidEventEnum, CrisalidTypeEnum
from services.crisalid.bus.consumer import on_event
from services.crisalid.interface import CrisalidService
from services.crisalid.models import (
    CrisalidConfig,
    Document,
    Researcher,
)
from services.crisalid.populates import PopulateDocument, PopulateResearcher
from services.crisalid.populates.caches import LiveCache
from services.crisalid.utils.bio import (
    generate_bio_from_researcher,
    generate_domains_from_researcher,
)

logger = logging.getLogger(__name__)


def get_crisalid_config(crisalid_config_id: int) -> CrisalidConfig:
    return CrisalidConfig.objects.select_related("organization").get(
        id=crisalid_config_id
    )


# TODO(remi): convert fields to graphql request

# https://github.com/CRISalid-esr/crisalid-ikg/blob/dev-main/app/amqp/amqp_person_event_message_factory.py#L28
# https://github.com/CRISalid-esr/crisalid-ikg/blob/dev-main/app/amqp/amqp_document_event_message_factory.py#L37


@on_event(CrisalidTypeEnum.PERSON, CrisalidEventEnum.CREATED)
@on_event(CrisalidTypeEnum.PERSON, CrisalidEventEnum.UPDATED)
@app.task(name=f"{__name__}.create_researcher")
def create_researcher(crisalid_config_id: int, fields: dict):
    config = get_crisalid_config(crisalid_config_id)
    logger.info("receive %s for organization %s", fields, config.organization)

    service = CrisalidService(config)

    # fetch data from apollo
    data = service.query("people", offset=0, limit=1, where={"uid_EQ": fields["uid"]})[
        "people"
    ]
    if not data:
        logger.warning("no result fetching crisalid_uid=%s", fields["uid"])
        return

    populate = PopulateResearcher(config)
    populate.single(data[0])


@on_event(CrisalidTypeEnum.PERSON, CrisalidEventEnum.DELETED)
@app.task(name=f"{__name__}.delete_researcher")
def delete_researcher(crisalid_config_id: int, fields: dict):
    config = get_crisalid_config(crisalid_config_id)
    logger.info("receive %s for organization %s", fields, config.organization)

    identifiers = [
        iden
        for iden in fields["identifiers"]
        if iden["harvester"].lower() not in Researcher.PRIVACY_HARVESTER
    ]

    # TODO(remi): check only one elements are deleted
    pks = Researcher.objects.from_identifiers(identifiers).values_list("pk", flat=True)
    deleted, _ = Researcher.objects.filter(pk__in=pks).delete()

    logger.info("deleted = %s", deleted)


@on_event(CrisalidTypeEnum.DOCUMENT, CrisalidEventEnum.CREATED)
@on_event(CrisalidTypeEnum.DOCUMENT, CrisalidEventEnum.UPDATED)
@app.task(name=f"{__name__}.create_document")
def create_document(crisalid_config_id: int, fields: dict):
    config = get_crisalid_config(crisalid_config_id)
    logger.info("receive %s for organization %s", fields, config.organization)

    service = CrisalidService(config)

    # fetch data from apollo
    data = service.query(
        "documents", offset=0, limit=1, where={"uid_EQ": fields["uid"]}
    )["documents"]
    if not data:
        logger.warning("no result fetching crisalid_uid=%s", fields["uid"])
        return

    populate = PopulateDocument(config)
    populate.single(data[0])


@on_event(CrisalidTypeEnum.DOCUMENT, CrisalidEventEnum.DELETED)
@app.task(name=f"{__name__}.delete_document")
def delete_document(crisalid_config_id: int, fields: dict):
    config = get_crisalid_config(crisalid_config_id)
    logger.info("receive %s for organization %s", fields, config.organization)

    identifiers = [
        {"harvester": iden["harvester"].lower(), "value": iden["uid"]}
        for iden in fields["recorded_by"]
    ]

    pks = Document.objects.from_identifiers(identifiers).values_list("pk", flat=True)
    deleted, _ = Document.objects.filter(pk__in=pks).delete()
    logger.info("deleted = %s", deleted)


# ----
# Vectorize documents for similarity
# ----
@app.task(name="Vectorize documents")
def vectorize_documents(documents_pks: list[int]):
    for obj in Document.objects.filter(pk__in=documents_pks):
        logger.debug("vectorize document=%s", obj)
        obj.vectorize()


# ----
# Vectorize researcher for similarity
# ----
@app.task(name="Vectorize researcher")
def vectorize_researchers(researchers_pks: list[int]):
    for obj in Researcher.objects.filter(pk__in=researchers_pks):
        logger.debug("vectorize researcher=%s", obj)
        obj.vectorize()


@app.task(name="Load json apollo data")
def load_apollo_data(crisalid_config_id: int, content: dict):
    config = get_crisalid_config(crisalid_config_id)
    logger.info("load apollo data file for organization %s", config.organization)

    cache = LiveCache()
    populate_researcher = PopulateResearcher(config, cache=cache)
    populate_document = PopulateDocument(config, cache=cache)

    for key, datas in content.items():
        if key == "people":
            populate_researcher.multiple(datas)
        elif key == "documents":
            populate_document.multiple(datas)


@app.task(name="Update Researcher Bio generate by Ia")
def update_researcher_domains(researcher_id: int):
    researcher = Researcher.objects.get(pk=researcher_id)
    logger.info("Update researcher Domains pk=%s", researcher.pk)

    generate_domains_from_researcher(researcher)


@app.task(name="Update Researcher Bio generate by Ia")
def update_researcher_bio_ia(researcher_id: int):
    researcher = Researcher.objects.get(pk=researcher_id)
    logger.info("Update researcher Bio pk=%s", researcher.pk)

    bio = generate_bio_from_researcher(researcher)
    short_bio = generate_bio_from_researcher(researcher, minimal=True)
    researcher.bio = bio
    researcher.short_bio = short_bio
    researcher.save()
    logger.info("Updated Researcher pk=%s bio successfully", researcher.pk)


@app.task(name="Update all Organization Researcher Bio generate by Ia")
def update_organization_researcher_bio_ia(organization_id: int):
    organization = Organization.objects.get(id=organization_id)
    # if organization is not enable ia, dont do it
    if not organization.enable_ia:
        logger.info(
            "Update researcher Bio from organization=%s not enabled", organization.code
        )
        return
    logger.info("Update researcher Bio from organization=%s enabled", organization.code)

    delta_update: datetime.timedelta = settings.RESEARCHER_DELTA_UPDATE_BIO
    last_update = datetime.datetime.now() - delta_update

    researchers_qs = Researcher.objects.filter(
        user__groups__organization=organization, updated_at__lt=last_update
    ).values_list("pk", flat=True)

    for researcher in researchers_qs:
        update_researcher_bio_ia.aplly_async((researcher.id,))
