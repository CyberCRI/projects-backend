import json
from unittest.mock import Mock

from django import test

from services.crisalid.bus.client import CrisalidBusClient
from services.crisalid.bus.constant import CrisalidEventEnum, CrisalidTypeEnum
from services.crisalid.bus.consumer import crisalid_consumer
from services.crisalid.factories import CrisalidConfigFactory


class TestCrisalidBus(test.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fields = {"id": 666, "value": "satan"}
        cls.payload = json.dumps(
            {
                "type": CrisalidTypeEnum.DOCUMENT.value,
                "event": CrisalidEventEnum.CREATED.value,
                "fields": cls.fields,
            }
        ).encode()
        cls.chanel = Mock()
        cls.properties = Mock()
        cls.method = Mock()

        cls.config = CrisalidConfigFactory()

    def setUp(self):
        self.client = CrisalidBusClient(self.config)
        crisalid_consumer.clean()

    def test_dispatch_no_callback(self):
        # this run withtout called any callback
        self.client._dispatch(self.chanel, self.properties, self.method, self.payload)

    def test_dispatch_with_callback(self):
        callback = Mock()
        crisalid_consumer.add_callback(
            CrisalidTypeEnum.DOCUMENT, CrisalidEventEnum.CREATED, callback
        )

        # this run withtout called any callback
        self.client._dispatch(self.chanel, self.properties, self.method, self.payload)

        # normaly is called
        callback.assert_called_once_with(
            self.config.organization.pk, json.loads(self.payload)["fields"]
        )

    def test_add_callback(self):
        callback = Mock()
        crisalid_consumer.add_callback(
            CrisalidTypeEnum.DOCUMENT, CrisalidEventEnum.CREATED, callback
        )

        # try to readd this callback, raise a exception
        with self.assertRaises(AssertionError):
            crisalid_consumer.add_callback(
                CrisalidTypeEnum.DOCUMENT, CrisalidEventEnum.CREATED, callback
            )

    def test_validated_payload(self):
        callback = Mock()
        crisalid_consumer.add_callback(
            CrisalidTypeEnum.DOCUMENT, CrisalidEventEnum.CREATED, callback
        )

        # this run withtout called any callback, invalid payload "string"
        payload = b""
        self.client._dispatch(self.chanel, self.properties, self.method, payload)
        callback.assert_not_called()

        # empty object {}
        payload = json.dumps({}).encode()
        self.client._dispatch(self.chanel, self.properties, self.method, payload)
        callback.assert_not_called()

        # invalid type
        payload = json.dumps(
            {
                "fields": {},
                "event": CrisalidEventEnum.CREATED.value,
                "type": "invalid_type",
            }
        ).encode()
        self.client._dispatch(self.chanel, self.properties, self.method, payload)
        callback.assert_not_called()

        # invalid event
        payload = json.dumps(
            {
                "fields": {},
                "type": CrisalidTypeEnum.DOCUMENT.value,
                "event": "invalid_event",
            }
        ).encode()
        self.client._dispatch(self.chanel, self.properties, self.method, payload)
        callback.assert_not_called()

        # invalid fields
        payload = json.dumps(
            {
                "fields": "",
                "type": CrisalidTypeEnum.DOCUMENT.value,
                "event": CrisalidEventEnum.CREATED.value,
            }
        ).encode()
        self.client._dispatch(self.chanel, self.properties, self.method, payload)
        callback.assert_not_called()

        # invalid decode str
        # invalid fields
        payload = json.dumps(
            {
                "fields": "",
                "type": CrisalidTypeEnum.DOCUMENT.value,
                "event": CrisalidEventEnum.CREATED.value,
            }
        ).encode("ascii")
        self.client._dispatch(self.chanel, self.properties, self.method, payload)
        callback.assert_not_called()
