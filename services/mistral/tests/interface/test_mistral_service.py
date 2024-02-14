from datetime import datetime
from unittest.mock import patch

from faker import Faker
from mistralai.models.chat_completion import (
    ChatCompletionResponse,
    ChatCompletionResponseChoice,
    ChatMessage,
    FinishReason,
    UsageInfo,
)
from mistralai.models.embeddings import EmbeddingObject, EmbeddingResponse

from apps.commons.test.testcases import JwtAPITestCase
from services.mistral.interface import MistralService

faker = Faker()


class MistralServiceTestCase(JwtAPITestCase):
    @patch("services.mistral.interface.MistralService.service.chat")
    def test_get_chat_response(self, mocked):
        responses = [faker.sentence(nb_words=6) for _ in range(3)]
        mocked.return_value = ChatCompletionResponse(
            id=faker.pystr(min_chars=32, max_chars=32),
            object="chat.completion",
            created=int(datetime.now().timestamp()),
            model="mistral-small",
            choices=[
                ChatCompletionResponseChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=response,
                    ),
                    finish_reason=FinishReason.stop,
                )
                for response in responses
            ],
            usage=UsageInfo(
                prompt_tokens=faker.pyint(min_value=1000, max_value=2000),
                total_tokens=faker.pyint(min_value=1000, max_value=2000),
                completion_tokens=faker.pyint(min_value=100, max_value=200),
            ),
        )
        response = MistralService.get_chat_response(
            system=[faker.sentence(nb_words=6) for _ in range(2)],
            prompt=[faker.sentence(nb_words=6) for _ in range(2)],
        )
        assert response == "\n".join(responses)

    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_get_embedding(self, mocked):
        embedding = [faker.pyfloat(min_value=0, max_value=1) for _ in range(1024)]
        mocked.return_value = EmbeddingResponse(
            id=faker.pystr(min_chars=32, max_chars=32),
            object="list",
            model="mistral-embed",
            data=[
                EmbeddingObject(
                    object="embedding",
                    embedding=embedding,
                    index=0,
                )
            ],
            usage=UsageInfo(
                prompt_tokens=faker.pyint(min_value=1000, max_value=2000),
                total_tokens=faker.pyint(min_value=1000, max_value=2000),
                completion_tokens=faker.pyint(min_value=100, max_value=200),
            ),
        )
        response = MistralService.get_embedding(faker.text())
        assert response == embedding
