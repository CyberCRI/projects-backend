from django import test

from services.crisalid.factories import CrisalidConfigFactory


class TestCrisalidTasks(test.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = CrisalidConfigFactory()
