import hashlib
from typing import TYPE_CHECKING, List, Optional

from django.db import models, transaction
from django.utils.html import strip_tags
from pgvector.django import CosineDistance, VectorField

from .interface import MistralService

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser
    from apps.projects.models import Project


class Embedding(models.Model):
    """
    Abstract class for models that store an embedding vector for another model.

    To set it up, you need to define the following attributes:
        - item: a OneToOneField to the model that will be embedded, it is advised
            to set an explicit related_name
        - embed_if_not_visible: whether to embed the item if it's not visible in
            vector_search results

    And the following methods:
        - set_visibility: a method that returns whether the item should be
            returned in vector_search results
        - get_summary_chat_system: a class method that returns the system messages
            for the chat prompt
        - get_summary_chat_prompt: a method that returns the user messages for the
            chat prompt
    """

    item: models.OneToOneField
    embed_if_not_visible: bool = False

    last_update = models.DateTimeField(auto_now=True)
    summary = models.TextField(blank=True)
    embedding = VectorField(dimensions=1024, null=True)
    is_visible = models.BooleanField(default=False)
    prompt_hashcode = models.CharField(max_length=64, default="")
    queued_for_update = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def set_visibility(self) -> bool:
        raise NotImplementedError()

    @classmethod
    def get_summary_chat_system(cls) -> List[str]:
        raise NotImplementedError()

    def get_summary_chat_prompt(self) -> List[str]:
        raise NotImplementedError()

    def get_summary(
        self,
        system: Optional[List[str]] = None,
        prompt: Optional[List[str]] = None,
        **kwargs,
    ) -> str:
        system = system or self.get_summary_chat_system()
        prompt = prompt or self.get_summary_chat_prompt()
        return MistralService.get_chat_response(system, prompt, **kwargs)

    def get_embedding(self, summary: Optional[str] = None, **kwargs) -> List[float]:
        summary = summary or self.get_summary(**kwargs)
        return MistralService.get_embedding(summary)

    def hash_prompt(self, prompt: Optional[List[str]] = None) -> str:
        prompt = prompt or self.get_summary_chat_prompt()
        prompt = "\n".join(prompt)
        return hashlib.sha256(prompt.encode()).hexdigest()

    @transaction.atomic
    def vectorize(self, summary: Optional[str] = None, **kwargs) -> "Embedding":
        is_visible = self.set_visibility()
        if not self.embed_if_not_visible and not is_visible:
            return self
        prompt = self.get_summary_chat_prompt()
        summary = summary or self.get_summary(prompt=prompt, **kwargs)
        embedding = self.get_embedding(summary)
        self.summary = summary
        self.embedding = embedding
        self.prompt_hashcode = self.hash_prompt(prompt)
        self.save()
        return self

    @classmethod
    def vector_search(
        cls, embedding: List[float], limit: int = 5
    ) -> List[models.Model]:
        related_model = cls.item.field.related_model
        related_name = cls.item.field.related_query_name()
        return related_model.objects.filter(
            **{f"{related_name}__is_visible": True}
        ).order_by(CosineDistance(f"{related_name}__embedding", embedding))[:limit]

    @classmethod
    def queue_or_create(cls, item: models.Model) -> "Embedding":
        instance, created = cls.objects.get_or_create(item=item)
        if created:
            return instance.vectorize()
        if instance.prompt_hashcode != instance.hash_prompt():
            instance.queued_for_update = True
            instance.save()
        return instance


class ProjectEmbedding(Embedding):
    item = models.OneToOneField(
        "projects.Project", on_delete=models.CASCADE, related_name="embedding"
    )
    embed_if_not_visible = False

    @property
    def project(self) -> "Project":
        return self.item

    def set_visibility(self) -> bool:
        is_visible = (
            len(self.project.description) > 10 or self.project.blog_entries.exists()
        )
        self.is_visible = is_visible
        self.save()
        return is_visible

    @classmethod
    def get_summary_chat_system(cls) -> List[str]:
        return [
            "CONTEXT : You are responsible for the portfolio of projects in your organization.",
            "OBJECTIVE : Generate a project profile from the following information.\
                - First give the project global objective\
                - Then give the project impact\
                - Then five the project summary",
            "STYLE: Easy to understand for an embedding model.",
            "TONE: Concise and explicit.",
            "AUDIENCE : An embedding model which will turn this summary into a vector.",
            "RESPONSE : The response must be a text of 120 words MAXIMUM.",
            "IMPORTANT : DO NOT MAKE UP ANY FACTS, EVEN IF IT MEANS RETURNING JUST A SENTENCE",
        ]

    def get_summary_chat_prompt(self) -> List[str]:
        """
        Return the prompt for the embedding model.
        """
        if len(self.project.description) > 10:
            content = strip_tags(self.project.description)[:10000]
        elif self.project.blog_entries.exists():
            blog_entry = self.project.blog_entries.first()
            title = blog_entry.title
            content = strip_tags(blog_entry.content)[:10000]
            content = f"{title}:\n{content}"
        else:
            content = ""
        if self.project.wikipedia_tags.exists():
            key_concepts = ", ".join(
                self.project.wikipedia_tags.all().values_list("name_en", flat=True)
            )
        else:
            key_concepts = ""
        return [
            f"Title : {self.project.title}",
            f"Purpose : {self.project.purpose}",
            f"Key concepts : {key_concepts}",
            f"Content : {content}",
        ]


class UserEmbedding(Embedding):
    item = models.OneToOneField(
        "accounts.ProjectUser", on_delete=models.CASCADE, related_name="embedding"
    )
    embed_if_not_visible = True

    @property
    def user(self) -> "ProjectUser":
        return self.item

    def set_visibility(self) -> bool:
        is_visible = (
            len(self.user.personal_description) > 10
            or len(self.user.professional_description) > 10
            or self.user.skills.filter(level__gte=3).exists()
        )
        self.is_visible = is_visible
        self.save()
        return is_visible

    @classmethod
    def get_summary_chat_system(cls) -> List[str]:
        return [
            "CONTEXT : You are responsible for the portfolio of people in your organization.",
            "OBJECTIVE : Generate a person's professional profile from the following information.",
            "STYLE: Easy to understand for an embedding model.",
            "TONE: Concise and explicit.",
            "AUDIENCE : An embedding model which will turn this summary into a vector.",
            "RESPONSE : The response must be a text of 120 words MAXIMUM.",
            "IMPORTANT : DO NOT MAKE UP ANY FACTS, EVEN IF IT MEANS RETURNING JUST A SENTENCE",
        ]

    def get_summary_chat_prompt(self) -> List[str]:
        expert_skills = self.user.skills.filter(level=4).values_list(
            "wikipedia_tag__name", flat=True
        )
        expert_skills = ", ".join(expert_skills) if expert_skills else ""
        competent_skills = self.user.skills.filter(level=3).values_list(
            "wikipedia_tag__name", flat=True
        )
        competent_skills = ", ".join(competent_skills) if competent_skills else ""
        description = "\n".join(
            [
                strip_tags(self.user.personal_description)[:5000],
                strip_tags(self.user.professional_description)[:5000],
            ]
        )
        return [
            f"Job: {self.user.job}",
            f"Expert in: {expert_skills}",
            f"Competent in: {competent_skills}",
            f"Biography: {description}",
        ]
