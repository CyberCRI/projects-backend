from unittest.mock import patch

from faker import Faker

from apps.commons.test import JwtAPITestCase
from services.mistral.interface import MistralService
from services.mistral.testcases import MistralTestCaseMixin

faker = Faker()


class MistralServiceTestCase(JwtAPITestCase, MistralTestCaseMixin):
    @patch("services.mistral.interface.MistralService.service.chat")
    def test_get_chat_response(self, mocked):
        messages = [faker.sentence() for _ in range(3)]
        mocked.return_value = self.chat_response_mocked_return(messages)
        response = MistralService.get_chat_response(
            system=[faker.sentence() for _ in range(2)],
            prompt=[faker.sentence() for _ in range(2)],
        )
        self.assertEqual(response, "\n".join(messages))

    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_get_embedding(self, mocked):
        embedding = [faker.pyfloat(min_value=0, max_value=1) for _ in range(1024)]
        mocked.return_value = self.embedding_response_mocked_return(embedding)
        response = MistralService.get_embedding(faker.text())
        self.assertEqual(response, embedding)
