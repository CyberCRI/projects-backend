import json
from typing import Any, Dict, List

from django.conf import settings
from mistralai import Mistral


class MistralService:
    service = Mistral(api_key=settings.MISTRAL_API_KEY)

    @classmethod
    def get_chat_response(cls, system: List[str], prompt: List[str], **kwargs) -> str:
        """
        Get the chat response from Mistral API.
        """
        messages = [
            *[{"content": message, "role": "system"} for message in system],
            *[{"content": message, "role": "user"} for message in prompt],
        ]
        response = cls.service.chat.complete(
            model="mistral-small", messages=messages, **kwargs
        )
        return "\n".join([choice.message.content for choice in response.choices])

    @classmethod
    def get_json_chat_response(
        cls, system: List[str], prompt: List[str], **kwargs
    ) -> Dict[str, Any]:
        messages = [
            *[{"content": message, "role": "system"} for message in system],
            *[{"content": message, "role": "user"} for message in prompt],
        ]
        response = cls.service.chat.complete(
            model="mistral-small",
            messages=messages,
            response_format={"type": "json_object"},
            **kwargs
        )
        return json.loads(response.choices[0].message.content)

    @classmethod
    def get_embedding(cls, prompt: str) -> List[float]:
        """
        Get the prompt's vector in 1024 dimensions from Mistral API.
        """
        response = cls.service.embeddings.create(
            model="mistral-embed",
            inputs=[prompt],
        )
        return response.data[0].embedding
