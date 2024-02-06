from typing import List
from django.conf import settings

from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage

from apps.accounts.models import ProjectUser
from apps.projects.models import Project


class MistralService:
    service = MistralClient(api_key=settings.MISTRAL_API_KEY)

    @classmethod
    def get_project_prompt(cls, project: Project) -> List[str]:
        messages = [
            "Summarize the following project:",
            f"Title : {project.title}",
            f"Key concepts : {','.join([t.name for t in project.wikipedia_tags.all()])}",
            f"Description : {project.description}",
        ]
        return [
            ChatMessage(role="user", content=message)
            for message in messages
        ]
    
    @classmethod
    def get_project_summary(cls, project: Project) -> str:
        prompt = cls.get_project_prompt(project)
        return cls.service.chat(
            model="mistral-small",
            messages = prompt
        )
    
    @classmethod
    def get_project_embeddings(cls, project: Project) -> list:
        projects_summary = cls.get_project_summary(project)
        return cls.service.embeddings(
            model="mistral-embed",
            input=[projects_summary],
        )


