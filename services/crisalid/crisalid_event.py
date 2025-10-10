import logging

from services.crisalid.crisalid_bus import (
    CrisalidEventEnum,
    CrisalidTypeEnum,
    on_event,
)
from services.crisalid.interface import CrisalidService
from services.crisalid.models import Publication, Researcher
from services.crisalid.populate import PopulatePublication, PopulateResearcher

logger = logging.getLogger(__name__)

# https://github.com/CRISalid-esr/crisalid-ikg/blob/dev-main/app/amqp/amqp_person_event_message_factory.py#L28
# https://github.com/CRISalid-esr/crisalid-ikg/blob/dev-main/app/amqp/amqp_document_event_message_factory.py#L37


@on_event(CrisalidTypeEnum.RESEARCH, CrisalidEventEnum.CREATED)
@on_event(CrisalidTypeEnum.RESEARCH, CrisalidEventEnum.UPDATED)
def create_researcher(fields: dict):
    logger.info("receive %s", fields)

    populate = PopulateResearcher()
    populate.single(fields)


@on_event(CrisalidTypeEnum.RESEARCH, CrisalidEventEnum.DELETED)
def delete_researcher(fields: dict):
    logger.info("receive %s", fields)

    deleted = Researcher.objects.filter(crisalid_uid=fields["uid"]).delete()
    logger.info("deleted = %s", deleted)


@on_event(CrisalidTypeEnum.DOCUMENT, CrisalidEventEnum.CREATED)
@on_event(CrisalidTypeEnum.DOCUMENT, CrisalidEventEnum.UPDATED)
def create_document(fields: dict):
    logger.info("receive %s", fields)

    service = CrisalidService()

    # fetch data from apollo
    data = service.query(
        "publications", offset=0, limit=1, where={"uid_EQ": fields["uid"]}
    )["documents"]
    if not data:
        logger.warning("no result fetching crisalid_uid=%s", fields["uid"])
        return

    populate = PopulatePublication()
    populate.single(data[0])


@on_event(CrisalidTypeEnum.DOCUMENT, CrisalidEventEnum.DELETED)
def delete_document(fields: dict):
    logger.error("receive %s", fields)

    deleted = Publication.objects.filter(crisalid_uid=fields["uid"]).delete()
    logger.info("deleted = %s", deleted)
