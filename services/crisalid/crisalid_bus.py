import enum
import json
import logging
from collections import defaultdict
from typing import Callable

import jsonschema
import pika
from celery import Task
from django.conf import settings

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
        self._channel = pika.channel.Channel
        self._run: bool = True
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
                self._channel = self.conn.channel()

                self._channel.queue_declare(queue=CrisalidBusClient.QUEUE_NAME)
                self._channel.basic_consume(
                    queue=CrisalidBusClient.QUEUE_NAME,
                    auto_ack=True,
                    on_message_callback=self._dispatch,
                )

                logger.info("Start channel Consuming")
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
        self._channel.cancel()
        self._channel = None

    def __delete__(self):
        # for disconnect when class is deleted
        self.disconnect()

    def _dispatch(
        self,
        chanel: pika.channel.Channel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes,
    ):
        """Global callback to get message, and dispatch on every listener"""

        logger.debug("Receive message tag=%r", method.delivery_tag)
        logger.debug("body: %s", body)

        # all message sended is json "stringify"
        try:
            body_str = body.decode()
            payload = json.loads(body_str)
        except UnicodeDecodeError as e:
            logger.exception("Impossible to decode bytes body: %s", str(e))
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

        # call callack in celery queue
        event_callback(payload["fields"])


# TODO(remi): nedd to create a singleton type ?
crisalid_bus_client = CrisalidBusClient()


# check methods is celery
def is_task_celery(func):
    return isinstance(func, Task) or (
        hasattr(func, "__wrapped__") and isinstance(func.__wrapped__, Task)
    )


# easy decorator method
def cdb_add_callback(
    crisalid_type: CrisalidTypeEnum, crisalid_event: CrisalidEventEnum
):
    def _wraps(func):
        func = func.apply if is_task_celery(func) else func
        crisalid_bus_client.add_callback(crisalid_type, crisalid_event, func)
        return func

    return _wraps
