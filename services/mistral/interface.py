from typing import List
from django.conf import settings

from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

from apps.projects.models import Project


class MistralService:
    service = MistralClient(api_key=settings.MISTRAL_API_KEY)

    @classmethod
    def get_project_prompt(cls, project: Project) -> List[str]:
        desc = project.description.replace('"', '')
        messages = [
            "Summarize the following project in about 150 words:",
            f"Title : {project.title}",
            f"Purpose : {project.purpose}",
            f"Key concepts : {', '.join(project.wikipedia_tags.all().values_list('name_en', flat=True))}",
            f"Description : {desc}",
        ]
        return [
            ChatMessage(role="user", content=message)
            for message in messages
        ]
    
    @classmethod
    def get_project_summary(cls, project: Project) -> str:
        prompt = cls.get_project_prompt(project)
        response = cls.service.chat(
            model="mistral-small",
            messages = prompt
        )
        return "\n".join([choice.message.content for choice in response.choices])
    
    @classmethod
    def get_project_embeddings(cls, project: Project) -> list:
        projects_summary = cls.get_project_summary(project)
        response = cls.service.embeddings(
            model="mistral-embed",
            input=[projects_summary],
        )
        return response.data[0].embedding
