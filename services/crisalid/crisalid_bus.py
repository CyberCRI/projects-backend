import enum
import json
import logging
from collections import defaultdict
from typing import Callable

import jsonschema
import pika
from django.conf import settings
from pika.adapters.blocking_connection import BlockingChannel

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

    QUEUE_NAME = "crisalid"

    def __init__(self):
        self.conn: pika.BlockingConnection | None = None
        self._run: bool = True
        self._consumer: dict[CrisalidTypeEnum, dict[CrisalidEventEnum, Callable]] = (
            defaultdict(lambda: defaultdict(lambda: None))
        )

    def add_callback(
        self, type: CrisalidTypeEnum, event: CrisalidEventEnum, callback: Callable
    ):
        assert (
            event.value not in self._consumer[type.value]
        ), f"Event {type}::{event}, is already set"

        # add callback
        self._consumer[type.value][event.value] = callback
        return callback

    def connect(self):
        assert self.conn is None, "rabimqt is already started"

        parameters = {
            "host": settings.CRISALID_BUS["host"],
            "port": settings.CRISALID_BUS["port"],
        }

        if not all(parameters.values()):
            logger.critical(
                "Can't instantiate CrisalidBus: invalid parameters, %s", parameters
            )
            return

        # run in loop to retry when connection is lost
        while self._run:
            try:

                logger.info("Create connection, parameters:%s", parameters)
                self.conn = pika.BlockingConnection(
                    pika.ConnectionParameters(**parameters)
                )
                channel = self.conn.channel()

                channel.queue_declare(queue=CrisalidBusClient.QUEUE_NAME)
                channel.basic_consume(
                    queue=CrisalidBusClient.QUEUE_NAME,
                    auto_ack=True,
                    on_message_callback=self._dispatch,
                )

                logger.info("Start Consuming")
                self._channel.start_consuming()
                break

            except pika.exceptions.ConnectionClosedByBroker:
                logger.error("Connection closed by crisalid broker")
            except pika.exceptions.AMQPChannelError as e:
                logger.error("Channel error: %s", str(e))
            except pika.exceptions.AMQPConnectionError as e:
                logger.error("Connection closed: %s", str(e))

        # ensure disconect after loop
        self._disconnect()

    def disconnect(self):
        """disconnect rabitmqt connection"""
        self._run = False
        if not self.conn:
            return

        self.logger.info("CrisalidBus connection closed")

        self.conn.close()
        self.conn = None

    def __delete__(self):
        # for disconnect when class is deleted
        self.disconnect()

    def _dispatch(
        self, chanel: BlockingChannel, method: str, properties: dict, body: str
    ):
        """Global callback to get message, and dispatch on every listener"""

        logger.debug("Receive message method=%r", method)
        logger.debug("body: %s", body)

        # all message sended is json "stringify"
        try:
            payload = json.loads(body)
        except (TypeError, ValueError) as e:
            logger.exception("Impossible to decode json body: %s", str(e))
            return

        # validate schema
        try:
            jsonschema.validate(payload, CRISALID_MESSAGE_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            logger.exception("Can't validate payload format: %s", str(e))
            return

        type = payload["type"]
        event = payload["event"]
        if not self._consumer[type][event]:
            logger.info("Not listener for event: %r", event)
            return

        event_callback = self._consumer[type][event]
        logger.debug("Call %s", event_callback)

        # call callack in celery queue
        event_callback(payload)


# TODO(remi): nedd to create a singleton type ?
crisalid_bus_client = CrisalidBusClient()
