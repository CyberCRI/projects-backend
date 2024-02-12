from typing import List

from django.conf import settings
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage


class MistralService:
    service = MistralClient(api_key=settings.MISTRAL_API_KEY)

    @classmethod
    def get_chat_response(cls, system: List[str], prompt: List[str], **kwargs) -> str:
        """
        adivsed kwargs for user:
        - temperature = 0.1 (default 0.7)
        - max_tokens = 500
        """
        system = [ChatMessage(role="system", content=message) for message in system]
        prompt = [ChatMessage(role="user", content=message) for message in prompt]
        response = cls.service.chat(
            model="mistral-small", messages=system + prompt, **kwargs
        )
        return "\n".join([choice.message.content for choice in response.choices])

    @classmethod
    def get_embedding(cls, prompt: str) -> List[float]:
        """
        Get the prompt's vector in 1024 dimensions from Mistral API.
        """
        response = cls.service.embeddings(
            model="mistral-embed",
            input=[prompt],
        )
        return response.data[0].embedding
