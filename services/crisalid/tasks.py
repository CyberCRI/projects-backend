import datetime
import logging

from django.conf import settings
from django.db import transaction

from apps.organizations.models import Organization
from projects.celery import app
from services.crisalid.bus.constant import CrisalidEventEnum, CrisalidTypeEnum
from services.crisalid.bus.consumer import on_event
from services.crisalid.interface import CrisalidService
from services.crisalid.models import (
    CrisalidConfig,
    Document,
    Researcher,
    ResearcherStructure,
    Structure,
)
from services.crisalid.populates import (
    PopulateAuthorityOrganization,
    PopulateDocument,
    PopulateJournal,
    PopulateResearcher,
    PopulateStructure,
)
from services.crisalid.populates.caches import LiveCache
from services.crisalid.utils.bio import (
    generate_bio_from_researcher,
    generate_domains_from_researcher,
)
from services.crisalid.utils.structures import sync_group_members, with_ancestors

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
    data = service.profile(fields["uid"])
    if not data:
        logger.warning("no result fetching crisalid_uid=%s", fields["uid"])
        return

    populate = PopulateResearcher(config)
    populate.single(data)


def person_identifiers(fields: dict) -> list[dict]:
    """identifiers of a person event (ikg format), without privacy identifiers"""
    return [
        {"harvester": iden["type"].lower(), "value": iden["value"]}
        for iden in fields["identifiers"]
        if iden["type"].lower() not in Researcher.PRIVACY_HARVESTER
    ]


@on_event(CrisalidTypeEnum.PERSON, CrisalidEventEnum.UNCHANGED)
@app.task(name=f"{__name__}.update_researcher_structures")
def update_researcher_structures(crisalid_config_id: int, fields: dict):
    """ikg sends "updated" only when identifiers changed, memberships/employments
    changes are sent as "unchanged" events
    """
    identifiers = person_identifiers(fields)
    if not identifiers:
        return
    researcher = Researcher.objects.from_identifiers(identifiers).first()
    # unknown researchers are created on "created" events
    if researcher is None:
        return

    # TODO: only fetch from graph when relations changed
    create_researcher(crisalid_config_id, fields)


@on_event(CrisalidTypeEnum.PERSON, CrisalidEventEnum.DELETED)
@app.task(name=f"{__name__}.delete_researcher")
def delete_researcher(crisalid_config_id: int, fields: dict):
    config = get_crisalid_config(crisalid_config_id)
    logger.info("receive %s for organization %s", fields, config.organization)

    identifiers = person_identifiers(fields)

    # TODO(remi): check only one elements are deleted
    pks = Researcher.objects.from_identifiers(identifiers).values_list("pk", flat=True)
    # researchers are no longer members of their structures groups
    structures = with_ancestors(
        Structure.objects.filter(
            pk__in=ResearcherStructure.objects.filter(researcher__in=pks).values(
                "structure"
            )
        )
    )
    deleted, _ = Researcher.objects.filter(pk__in=pks).delete()
    for structure in structures:
        sync_group_members(structure)

    logger.info("deleted = %s", deleted)


@on_event(CrisalidTypeEnum.DOCUMENT, CrisalidEventEnum.CREATED)
@on_event(CrisalidTypeEnum.DOCUMENT, CrisalidEventEnum.UPDATED)
@app.task(name=f"{__name__}.create_document")
def create_document(crisalid_config_id: int, fields: dict):
    config = get_crisalid_config(crisalid_config_id)
    logger.info("receive %s for organization %s", fields, config.organization)

    service = CrisalidService(config)

    # fetch data from apollo
    data = service.document(fields["uid"])
    if not data:
        logger.warning("no result fetching crisalid_uid=%s", fields["uid"])
        return

    populate = PopulateDocument(config)
    populate.single(data)


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


@on_event(CrisalidTypeEnum.STRUCTURE, CrisalidEventEnum.CREATED)
@on_event(CrisalidTypeEnum.STRUCTURE, CrisalidEventEnum.UPDATED)
@app.task(name=f"{__name__}.create_structure")
def create_structure(crisalid_config_id: int, fields: dict):
    config = get_crisalid_config(crisalid_config_id)
    logger.info("receive %s for organization %s", fields, config.organization)

    service = CrisalidService(config)
    uid = fields["uid"]

    # fetch data from apollo
    data = service.structure(uid)
    if not data:
        logger.warning("no result fetching crisalid_uid=%s", uid)
        return

    # structures and people related to this one already have their relations:
    # they created it (node only) if it was missing
    PopulateStructure(config).single(data)


@on_event(CrisalidTypeEnum.STRUCTURE, CrisalidEventEnum.DELETED)
@app.task(name=f"{__name__}.delete_structure")
def delete_structure(crisalid_config_id: int, fields: dict):
    config = get_crisalid_config(crisalid_config_id)
    logger.info("receive %s for organization %s", fields, config.organization)

    structure = Structure.objects.filter(
        organization=config.organization, crisalid_uid=fields["uid"]
    ).first()
    if structure is None:
        return

    # sub-structures members are no longer members of ancestors groups
    ancestors = structure.ancestors()
    with transaction.atomic():
        if structure.people_group:
            structure.people_group.delete()
        structure.delete()
    for ancestor in ancestors:
        sync_group_members(ancestor)


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
    # same order as the initial import
    populates = (
        ("authorityOrganizations", PopulateAuthorityOrganization(config, cache=cache)),
        ("journals", PopulateJournal(config, cache=cache)),
        ("organizationUnits", PopulateStructure(config, cache=cache)),
        ("people", PopulateResearcher(config, cache=cache)),
        ("documents", PopulateDocument(config, cache=cache)),
    )
    for key, populate in populates:
        if key in content:
            populate.multiple(content[key])


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
