import json
from typing import Any

from django.conf import settings
from mistralai.client import Mistral
from mistralai.client.models import JSONSchema, ResponseFormat


class MistralService:
    service = Mistral(api_key=settings.MISTRAL_API_KEY)

    @classmethod
    def get_chat_response(cls, system: list[str], prompt: list[str], **kwargs) -> str:
        """
        Get the chat response from Mistral API.
        """
        messages = [
            *[{"content": message, "role": "system"} for message in system],
            *[{"content": message, "role": "user"} for message in prompt],
        ]
        response = cls.service.chat.complete(
            model=settings.MISTRAL_COMPLETION_MODEL, messages=messages, **kwargs
        )
        return "\n".join([choice.message.content for choice in response.choices])

    @classmethod
    def get_structured_chat_response(
        cls,
        system: list[str],
        prompt: list[str],
        json_schema: dict[str, Any],
        name: str = "response",
        **kwargs,
    ) -> dict[str, Any]:
        """
        Get a chat response constrained to the given JSON schema.
        """
        messages = [
            *[{"content": message, "role": "system"} for message in system],
            *[{"content": message, "role": "user"} for message in prompt],
        ]
        response = cls.service.chat.complete(
            model=settings.MISTRAL_COMPLETION_MODEL,
            messages=messages,
            response_format=ResponseFormat(
                type="json_schema",
                json_schema=JSONSchema(
                    name=name, schema_definition=json_schema, strict=True
                ),
            ),
            **kwargs,
        )
        return json.loads(response.choices[0].message.content)

    @classmethod
    def get_embedding(cls, prompt: str) -> list[float]:
        """
        Get the prompt's vector in 1024 dimensions from Mistral API.
        """
        response = cls.service.embeddings.create(
            model=settings.MISTRAL_EMBEDDING_MODEL, inputs=[prompt]
        )
        return response.data[0].embedding
