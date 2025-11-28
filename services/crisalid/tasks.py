import logging

from projects.celery import app
from services.crisalid.apps import CrisalidConfig
from services.crisalid.bus.constant import CrisalidEventEnum, CrisalidTypeEnum
from services.crisalid.bus.consumer import on_event
from services.crisalid.interface import CrisalidService
from services.crisalid.models import Document, Identifier, Researcher
from services.crisalid.populates import PopulateDocument, PopulateResearcher

logger = logging.getLogger(__name__)


def get_crisalid_config(crisalid_config_id: int) -> CrisalidConfig:
    return CrisalidConfig.objects.get(id=crisalid_config_id).selected_related(
        "organization"
    )


# https://github.com/CRISalid-esr/crisalid-ikg/blob/dev-main/app/amqp/amqp_person_event_message_factory.py#L28
# https://github.com/CRISalid-esr/crisalid-ikg/blob/dev-main/app/amqp/amqp_document_event_message_factory.py#L37


@on_event(CrisalidTypeEnum.PERSON, CrisalidEventEnum.CREATED)
@on_event(CrisalidTypeEnum.PERSON, CrisalidEventEnum.UPDATED)
@app.task(name=f"{__name__}.create_person")
def create_person(crisalid_config_id: int, fields: dict):
    config = get_crisalid_config(crisalid_config_id)
    logger.error("receive %s for organization %s", fields, config.organization)

    populate = PopulateResearcher(config)
    populate.single(fields)


@on_event(CrisalidTypeEnum.PERSON, CrisalidEventEnum.DELETED)
@app.task(name=f"{__name__}.delete_person")
def delete_person(crisalid_config_id: int, fields: dict):
    config = get_crisalid_config(crisalid_config_id)
    logger.error("receive %s for organization %s", fields, config.organization)

    identifiers = [
        {"harvester": iden["type"].lower(), "value": iden["value"]}
        for iden in fields["identifiers"]
        if iden["type"].lower()
        not in (Identifier.Harvester.LOCAL, Identifier.Harvester.EPPN)
    ]

    deleted = Researcher.objects.from_identifiers(identifiers).delete()
    logger.info("deleted = %s", deleted)


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

    deleted = Document.objects.from_identifiers(identifiers).delete()
    logger.info("deleted = %s", deleted)
