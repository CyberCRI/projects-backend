from typing import List
from django.utils.html import strip_tags

from django.conf import settings
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from apps.accounts.models import ProjectUser

from apps.projects.models import Project


class MistralService:
    service = MistralClient(api_key=settings.MISTRAL_API_KEY)

    @classmethod
    def get_project_prompt(cls, project: Project) -> List[str]:
        desc = strip_tags(project.description).replace('"', "")[:10000]
        messages = [
            "Generate a project profile from the following project information. Start by giving the project global objective, then its impact, then a summary. Strictly limit the summary to 100 words."
            f"Title : {project.title}",
            f"Purpose : {project.purpose}",
            f"Key concepts : {', '.join(project.wikipedia_tags.all().values_list('name_en', flat=True))}",
            f"Description : {desc}",
        ]
        return [ChatMessage(role="user", content=message) for message in messages]
    
    @classmethod
    def get_user_prompt(cls, user: ProjectUser) -> List[str]:
        expert_skills = user.skills.filter(level=4).values_list('wikipedia_tag__name', flat=True)
        competent_skills = user.skills.filter(level=3).values_list('wikipedia_tag__name', flat=True)
        description = strip_tags(user.personal_description)[:5000] + "\n" + strip_tags(user.professional_description)[:5000]
        if not expert_skills and not competent_skills and len(description) <= 10:
            raise ValueError("Not enough info to vectorize")
        messages = [
            "Generate a very short paragraph (less than 100 words) describing factually an unnamed person from the following information:",
            f"Their job is {user.job} " if user.job else "",
            f"They are expert in {', '.join(expert_skills)} " if expert_skills else "",
            f"They are competent in {', '.join(competent_skills)} " if competent_skills else "",
            f"Biography: {description}" if len(description) > 10 else "",
            "Do not make up any facts. If you do not know much, just state the role of the person like 'this person role is XXX.' Stop there. Do not explain the role"
        ]
        return [ChatMessage(role="user", content=message) for message in messages if message]
        

    @classmethod
    def get_project_summary(cls, project: Project) -> str:
        prompt = cls.get_project_prompt(project)
        response = cls.service.chat(model="mistral-small", messages=prompt)
        return "\n".join([choice.message.content for choice in response.choices])
    
    @classmethod
    def get_user_summary(cls, user: ProjectUser) -> str:
        prompt = cls.get_user_prompt(user)
        response = cls.service.chat(
            model="mistral-small",
            messages=prompt,
            temperature = 0.1, #default 0.7
            max_tokens = 200,

        )
        return "\n".join([choice.message.content for choice in response.choices])

    @classmethod
    def get_embeddings(cls, prompt: str) -> List[float]:
        response = cls.service.embeddings(
            model="mistral-embed",
            input=[prompt],
        )
        return response.data[0].embedding

    @classmethod
    def vectorize_project(cls, project: Project) -> Project:
        summary = cls.get_project_summary(project)
        embeddings = cls.get_embeddings(summary)
        project = Project.objects.filter(pk=project.pk)
        project.update(generated_summary=summary, summary_embedding=embeddings)
        return project.get()
    
    @classmethod
    def vectorize_user(cls, user: ProjectUser) -> ProjectUser:
        try:
            summary = cls.get_user_summary(user)
            embeddings = cls.get_embeddings(summary)
            user = ProjectUser.objects.filter(pk=user.pk)
            user.update(generated_summary=summary, summary_embedding=embeddings)
            return user.get()
        except ValueError as e:
            print("error while vectorizing", e)
            return None
