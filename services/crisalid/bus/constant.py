import enum

from services.crisalid.models import Structure


# https://github.com/CRISalid-esr/crisalid-deployment/blob/6b37862bb27b0e2164666f9e8b049ac3dbf60923/docker/crisalid-bus/definitions.sample.json#L7
# Event/Type from crisalid https://github.com/CRISalid-esr/crisalid-ikg/tree/dev-main/app/amqp
class CrisalidTypeEnum(enum.StrEnum):
    PERSON = "person"
    STRUCTURE = "structure"
    HARVESTING = "harvesting_result_event"
    DOCUMENT = "document"


class CrisalidEventEnum(enum.StrEnum):
    """Event from crisalid
    "unchanged" event is only used for people (memberships/employments changes)
    """

    UPDATED = "updated"
    CREATED = "created"
    DELETED = "deleted"
    UNCHANGED = "unchanged"


# schema received from crisalid
CRISALID_MESSAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {
            "enum": [v.value for v in CrisalidTypeEnum] + Structure.GenericType.values
        },
        "event": {"enum": [v.value for v in CrisalidEventEnum]},
        "fields": {
            "type": "object"
            # TODO(remi): speficied all fields types ?
        },
    },
    "required": ["type", "event", "fields"],
}
