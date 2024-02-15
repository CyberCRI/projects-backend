from datetime import datetime
from typing import List

from faker import Faker
from mistralai.models.chat_completion import (
    ChatCompletionResponse,
    ChatCompletionResponseChoice,
    ChatMessage,
    FinishReason,
    UsageInfo,
)
from mistralai.models.embeddings import EmbeddingObject, EmbeddingResponse

faker = Faker()


class MistralTestCaseMixin:
    def chat_response_mocked_return(self, messages: List[str]):
        return ChatCompletionResponse(
            id=faker.pystr(min_chars=32, max_chars=32),
            object="chat.completion",
            created=int(datetime.now().timestamp()),
            model="mistral-small",
            choices=[
                ChatCompletionResponseChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=message,
                    ),
                    finish_reason=FinishReason.stop,
                )
                for message in messages
            ],
            usage=UsageInfo(
                prompt_tokens=faker.pyint(min_value=1000, max_value=2000),
                total_tokens=faker.pyint(min_value=1000, max_value=2000),
                completion_tokens=faker.pyint(min_value=100, max_value=200),
            ),
        )

    def embedding_response_mocked_return(self, embedding: List[float]):
        return EmbeddingResponse(
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
