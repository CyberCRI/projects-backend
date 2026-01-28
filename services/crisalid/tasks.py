import logging

from projects.celery import app
from services.crisalid.bus.constant import CrisalidEventEnum, CrisalidTypeEnum
from services.crisalid.bus.consumer import on_event
from services.crisalid.interface import CrisalidService
from services.crisalid.models import (
    CrisalidConfig,
    Document,
    Identifier,
    Researcher,
    Structure,
)
from services.crisalid.populates import PopulateDocument, PopulateResearcher
from services.crisalid.populates.structure import PopulateStructure

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
    logger.error("receive %s for organization %s", fields, config.organization)

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
    logger.error("receive %s for organization %s", fields, config.organization)

    identifiers = [
        {"harvester": iden["type"].lower(), "value": iden["value"]}
        for iden in fields["identifiers"]
        if iden["type"].lower()
        not in (Identifier.Harvester.LOCAL, Identifier.Harvester.EPPN)
    ]

    # TODO(remi): check only one elements are deleted
    pks = Researcher.objects.from_identifiers(identifiers).values_list("pk", flat=True)
    deleted, _ = Researcher.objects.filter(pk__in=pks).delete()

    logger.info("deleted = %s", deleted)


# ----
# Documents task (publications/conference ....)
# ----
@on_event(CrisalidTypeEnum.STRUCTURE, CrisalidEventEnum.CREATED)
@on_event(CrisalidTypeEnum.STRUCTURE, CrisalidEventEnum.UPDATED)
@app.task(name=f"{__name__}.create_structure")
def create_structure(crisalid_config_id: int, fields: dict):
    config = get_crisalid_config(crisalid_config_id)
    logger.error("receive %s for organization %s", fields, config.organization)

    service = CrisalidService(config)

    # fetch data from apollo
    data = service.query(
        "organisations", offset=0, limit=1, where={"uid_EQ": fields["uid"]}
    )["organisations"]
    if not data:
        logger.warning("no result fetching crisalid_uid=%s", fields["uid"])
        return

    populate = PopulateStructure(config)
    populate.single(data[0])


@on_event(CrisalidTypeEnum.STRUCTURE, CrisalidEventEnum.DELETED)
@app.task(name=f"{__name__}.delete_structure")
def delete_structure(crisalid_config_id: int, fields: dict):
    config = get_crisalid_config(crisalid_config_id)
    logger.error("receive %s for organization %s", fields, config.organization)

    identifiers = [
        {"harvester": iden["type"].lower(), "value": iden["value"]}
        for iden in fields["identifiers"]
        if iden["type"].lower()
        not in (Identifier.Harvester.LOCAL, Identifier.Harvester.EPPN)
    ]

    qs = Structure.objects.from_identifiers(identifiers, distinct=False).filter(
        organization=config.organization
    )
    deleted, _ = qs.delete()

    logger.info("deleted = %s", deleted)


# ----
# Documents task (publications/conference ....)
# ----
@on_event(CrisalidTypeEnum.DOCUMENT, CrisalidEventEnum.CREATED)
@on_event(CrisalidTypeEnum.DOCUMENT, CrisalidEventEnum.UPDATED)
@app.task(name=f"{__name__}.create_document")
def create_document(crisalid_config_id: int, fields: dict):
    config = get_crisalid_config(crisalid_config_id)
    logger.error("receive %s for organization %s", fields, config.organization)

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
    logger.error("receive %s for organization %s", fields, config.organization)

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
