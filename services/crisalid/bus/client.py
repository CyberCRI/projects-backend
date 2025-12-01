import json
import logging
import time

import jsonschema
import pika
from urllib3.util import parse_url

from services.crisalid.bus.constant import CRISALID_MESSAGE_SCHEMA, CrisalidEventEnum
from services.crisalid.models import CrisalidConfig

from .consumer import crisalid_consumer


class CrisalidBusClient:
    """Class to connect to crisalid rabitmqt, and receive all event messages."""

    # queue create by ikg for send messages
    CRISALID_EXCHANGE = "graph"
    # routing key ikg send event (the * is for listen on all event (updated,created,deleted))
    CRISALID_ROUTING_KEYS = []
    for event in CrisalidEventEnum:
        CRISALID_ROUTING_KEYS.extend(
            (
                f"event.people.person.{event.value}",
                f"event.structures.structure.{event.value}",
                f"event.documents.document.{event.value}",
            )
        )

    def __init__(self, config: CrisalidConfig):
        self.config = config
        self.conn: pika.BlockingConnection | None = None
        self._channel = pika.channel.Channel
        self._run: bool = True
        self.logger = logging.getLogger(config.organization.code)

    def parameters(self) -> dict | None:
        """generate parametrs for crislaid and check values"""

        # url is complte (ex: "http://crisalid:4325")
        # get url without port, and set port for pika
        url = parse_url(self.config.crisalidbus_url)
        parameters = {
            "host": url.host,
            "port": url.port,
            "user": self.config.crisalidbus_username,
            "password": self.config.crisalidbus_password,
        }

        if not all(parameters.values()):
            # safe remove password to not showing in log
            if parameters["password"]:
                parameters["password"] = "*" * 10
            self.logger.critical(
                "Can't instantiate CrisalidBus: invalid parameters, %s", parameters
            )
            return None

        return parameters

    def connect(self):
        assert self.conn is None, "rabimqt is already started"

        parameters = self.parameters()

        retry = 1
        # run in loop to retry when connection is lost
        while self._run:
            try:
                self.logger.info("Create pika connection")

                credentials = pika.PlainCredentials(
                    parameters["user"], parameters["password"]
                )

                self.conn = pika.BlockingConnection(
                    pika.ConnectionParameters(
                        host=parameters["host"],
                        port=parameters["port"],
                        credentials=credentials,
                        virtual_host="/",
                    ),
                )
                self._channel = self.conn.channel()
                exchange = self.CRISALID_EXCHANGE
                self._channel.exchange_declare(
                    exchange=exchange, exchange_type="topic", durable=True
                )
                queue_name = f"projects-backend.{exchange}"
                self._channel.queue_declare(queue=queue_name, exclusive=True)
                for routing_key in self.CRISALID_ROUTING_KEYS:
                    self._channel.queue_bind(
                        exchange=exchange, queue=queue_name, routing_key=routing_key
                    )

                self._channel.basic_consume(
                    queue=queue_name, on_message_callback=self._dispatch, auto_ack=True
                )

                self.logger.info("Start channel Consuming")
                self._channel.start_consuming()
                break

            except pika.exceptions.ConnectionClosedByBroker:
                self.logger.error("Connection closed by crisalid broker")
            except pika.exceptions.AMQPChannelError as e:
                self.logger.error("Channel error: %s", str(e))
            except pika.exceptions.AMQPConnectionError as e:
                self.logger.error("Connection closed: %s", str(e))

            if not self._run:
                break

            # incremental retry (max 60s)
            retry = min(retry * 2, 60)
            time.sleep(retry)

        # ensure disconect after loop
        self._disconnect()

    def disconnect(self):
        """disconnect rabitmqt connection"""
        self._run = False
        if not self.conn:
            return

        self.self.logger.info("CrisalidBus connection closed")

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

        self.logger.info("Receive routingkey=%r", method.routing_key)
        self.logger.debug("body: %s", body)

        # all message sended is json binary "stringify"
        try:
            body_str = body.decode()
            payload = json.loads(body_str)
        except UnicodeDecodeError as e:
            self.logger.exception("Impossible to decode bytes body: %s", str(e))
            return
        except (TypeError, ValueError) as e:
            self.logger.exception("Impossible to decode json body: %s", str(e))
            return

        # validate schema
        try:
            jsonschema.validate(payload, CRISALID_MESSAGE_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            self.logger.exception("Can't validate payload format: %s", str(e))
            return

        crisalid_type = payload["type"]
        crisalid_event = payload["event"]
        if not crisalid_consumer[crisalid_type][crisalid_event]:
            self.logger.info(
                "Not listener for event: %s::%s", crisalid_type, crisalid_event
            )
            return

        event_callback = crisalid_consumer[crisalid_type][crisalid_event]
        self.logger.debug("Call %s", event_callback)

        fields = payload["fields"]
        event_callback(self.config.pk, fields)
