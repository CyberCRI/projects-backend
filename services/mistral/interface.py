from typing import List

from django.conf import settings
from mistralai import Mistral


class MistralService:
    service = Mistral(api_key=settings.MISTRAL_API_KEY)

    @classmethod
    def get_chat_response(cls, system: List[str], prompt: List[str], **kwargs) -> str:
        """
        Get the chat response from Mistral API.
        """
        system = [{"content": message, "role": "system"} for message in system]
        prompt = [{"content": message, "role": "user"} for message in prompt]
        response = cls.service.chat.complete(
            model="mistral-small", messages=system + prompt, **kwargs
        )
        return "\n".join([choice.message.content for choice in response.choices])

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
