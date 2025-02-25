from faker import Faker
from parameterized import parameterized

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.skills.models import Mentoring
from apps.skills.serializers import (
    MentoringContactSerializer,
    MentoringResponseSerializer,
)

faker = Faker()


class MockedRequest:
    def __init__(self, user):
        self.user = user


class MiscMentoringTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory()
        cls.request = MockedRequest(cls.user)

    @parameterized.expand(
        [
            (faker.email(),),
            (None,),
            ("",),
        ]
    )
    def test_mentoring_contact_serializer(self, reply_to):
        data = {
            "content": faker.text(),
            "reply_to": reply_to,
        }
        serializer = MentoringContactSerializer(
            data=data, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())
        if reply_to:
            self.assertEqual(serializer.validated_data["reply_to"], reply_to)
        else:
            self.assertEqual(serializer.validated_data["reply_to"], self.user.email)

    def test_mentoring_contact_serializer_no_reply_to(self):
        data = {
            "content": faker.text(),
        }
        serializer = MentoringContactSerializer(
            data=data, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["reply_to"], self.user.email)

    @parameterized.expand(
        [
            (faker.email(),),
            (None,),
            ("",),
        ]
    )
    def test_mentoring_response_serializer(self, reply_to):
        data = {
            "status": Mentoring.MentoringStatus.ACCEPTED,
            "content": faker.text(),
            "reply_to": reply_to,
        }
        serializer = MentoringResponseSerializer(
            data=data, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())
        if reply_to:
            self.assertEqual(serializer.validated_data["reply_to"], reply_to)
        else:
            self.assertEqual(serializer.validated_data["reply_to"], self.user.email)

    def test_mentoring_response_serializer_no_reply_to(self):
        data = {
            "status": Mentoring.MentoringStatus.ACCEPTED,
            "content": faker.text(),
        }
        serializer = MentoringResponseSerializer(
            data=data, context={"request": self.request}
        )
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data["reply_to"], self.user.email)
