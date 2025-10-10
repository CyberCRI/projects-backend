import enum
import json
import logging
from collections import defaultdict
from typing import Callable

import jsonschema

logger = logging.getLogger(__name__)


# Event/Type from crisalid https://github.com/CRISalid-esr/crisalid-ikg/tree/dev-main/app/amqp
class CrisalidTypeEnum(enum.StrEnum):
    PERSONE = "persone"
    RESEARCH = "research_structure"
    HARVESTING = "harvesting_result_event"
    DOCUMENT = "document"


class CrisalidEventEnum(enum.StrEnum):
    UPDATED = "updated"
    CREATED = "created"
    DELETED = "deleted"
    UNCHANGED = "unchanged"


# schema received from crisalid
CRISALID_MESSAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "type": {
            "enum": [v.value for v in CrisalidTypeEnum],
        },
        "event": {
            "enum": [v.value for v in CrisalidEventEnum],
        },
        "fields": {
            "type": "object"
            # TODO(remi): speficied all fields types ?
        },
    },
    "required": ["type", "event", "fields"],
}


class CrisalidBusClient:
    """Class to connect to crisalid rabitmqt, and receive all event messages."""

    def __init__(self):
        self._consumer: dict[CrisalidTypeEnum, dict[CrisalidEventEnum, Callable]] = (
            defaultdict(lambda: defaultdict(lambda: None))
        )

    def add_callback(
        self,
        crisalid_type: CrisalidTypeEnum,
        crisalid_event: CrisalidEventEnum,
        callback: Callable,
    ):
        assert (
            crisalid_event.value not in self._consumer[crisalid_type.value]
        ), f"Event {crisalid_type}::{crisalid_event}, is already set"

        # add callback
        self._consumer[crisalid_type.value][crisalid_event.value] = callback
        return callback

    def _dispatch(
        self,
        body: str,
    ):
        """Global callback to get message, and dispatch on every listener"""

        logger.debug("body: %s", body)

        # all message sended is json "stringify"
        try:
            payload = json.loads(body)
        except UnicodeDecodeError as e:
            logger.exception("Impossible to decode body: %s", str(e))
            return
        except (TypeError, ValueError) as e:
            logger.exception("Impossible to decode json body: %s", str(e))
            return

        # validate schema
        try:
            jsonschema.validate(payload, CRISALID_MESSAGE_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            logger.exception("Can't validate payload format: %s", str(e))
            return

        crisalid_type = payload["type"]
        crisalid_event = payload["event"]
        if not self._consumer[crisalid_type][crisalid_event]:
            logger.info("Not listener for event: %s::%s", crisalid_type, crisalid_event)
            return

        event_callback = self._consumer[crisalid_type][crisalid_event]
        logger.debug("Call %s", event_callback)

        fields = payload["fields"]
        event_callback(fields)


# TODO(remi): nedd to create a singleton type ?
crisalid_bus_client = CrisalidBusClient()


# easy decorator method
def on_event(crisalid_type: CrisalidTypeEnum, crisalid_event: CrisalidEventEnum):
    """shortcut decorator to crisalid_bus.add_callback

    :param crisalid_type: crisalid type name
    :param crisalid_event: crisalid event name
    """

    def _wraps(func):
        crisalid_bus_client.add_callback(crisalid_type, crisalid_event, func)
        return func

    return _wraps
