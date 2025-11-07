import hashlib
import itertools
import traceback
from typing import TYPE_CHECKING

from django.db import models, transaction
from django.db.models import QuerySet
from django.utils.html import strip_tags
from pgvector.django import CosineDistance, VectorField

from apps.commons.models import GroupData
from apps.projects.models import Project

from .exceptions import VectorSearchWrongQuerysetError
from .interface import MistralService

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser
    from apps.skills.models import Tag


class HasWeight:
    """
    Abstract class for models that have a weight in an average vector.
    """

    def get_weight(self) -> float:
        raise NotImplementedError()


class EmbeddingError(models.Model):
    """
    Model to store errors that occurred during the generation of an embedding.
    """

    item_type = models.CharField(max_length=255)
    item_id = models.CharField(max_length=255)
    error = models.CharField(max_length=255)
    traceback = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Error for {self.item_type} {self.item_id}: {self.error}"


class Embedding(models.Model):
    """
    Abstract class for models that store an embedding vector for another model.

    To set it up, you need to define the following attributes:
        - item: a OneToOneField to the model that will be embedded, it is advised
            to set an explicit related_name

    And the following methods:
        - get_is_visible: a method that returns whether the item should be
            returned in vector_search results
        - set_embedding: a method that sets the embedding of the item and returns
            the instance
    """

    item: models.OneToOneField

    last_update = models.DateTimeField(auto_now=True)
    embedding = VectorField(dimensions=1024, null=True)
    is_visible = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def get_is_visible(self) -> bool:
        raise NotImplementedError()

    def set_embedding(self, *args, **kwargs) -> "Embedding":
        raise NotImplementedError()

    def set_visibility(self) -> bool:
        is_visible = self.get_is_visible()
        if self.is_visible != is_visible:
            self.is_visible = is_visible
            self.save(update_fields=["is_visible"])
        return is_visible

    def vectorize(self, *args, **kwargs) -> "Embedding":
        try:
            with transaction.atomic():
                if self.set_visibility():
                    return self.set_embedding(*args, **kwargs)
                if self.embedding is not None:
                    self.embedding = None
                    self.save()
        except Exception as e:  # noqa: PIE786
            EmbeddingError.objects.create(
                item_type=self.item.__class__.__name__,
                item_id=self.item.id,
                error=e.__class__.__name__,
                traceback=traceback.format_exc(),
            )
        return self

    @classmethod
    def vector_search(
        cls, embedding: list[float], queryset: QuerySet | None = None
    ) -> QuerySet:
        queryset = queryset or cls.item.field.related_model.objects
        if not queryset.model == cls.item.field.related_model:
            raise VectorSearchWrongQuerysetError
        related_name = cls.item.field.related_query_name()
        return queryset.filter(**{f"{related_name}__is_visible": True}).order_by(
            CosineDistance(f"{related_name}__embedding", embedding)
        )


class MistralEmbedding(Embedding):
    """
    Abstract class for models that store an embedding vector for another model.
    The embedding is generated using the Mistral API.

    To set it up, you need to define the following attributes:
        - item: a OneToOneField to the model that will be embedded, it is advised
            to set an explicit related_name
        - temperature: the temperature to use for the chat prompt (API default is 0.7)
        - max_tokens: the maximum number of tokens to use for the chat prompt

    And the following methods:
        - get_is_visible: a method that returns whether the item should be
            returned in vector_search results
        - get_summary_chat_system: a class method that returns the system messages
            for the chat prompt
        - get_summary_chat_prompt: a method that returns the user messages for the
            chat prompt
    """

    temperature: float | None = None
    max_tokens: int | None = None
    summary = models.TextField(blank=True)
    prompt_hashcode = models.CharField(max_length=64, default="")

    class Meta:
        abstract = True

    @classmethod
    def get_summary_chat_system(cls) -> list[str]:
        raise NotImplementedError()

    def get_summary_chat_prompt(self) -> list[str]:
        raise NotImplementedError()

    def set_embedding(
        self, summary: str | None = None, *args, **kwargs
    ) -> "MistralEmbedding":
        if self.prompt_hashcode != self.hash_prompt():
            prompt = self.get_summary_chat_prompt()
            summary = summary or self.get_summary(prompt=prompt)
            self.summary = summary
            self.embedding = MistralService.get_embedding(summary) or None
            self.prompt_hashcode = self.hash_prompt(prompt)
            self.save()
        return self

    def hash_prompt(self, prompt: list[str] | None = None) -> str:
        prompt = prompt or self.get_summary_chat_prompt()
        prompt = "\n".join(prompt)
        return hashlib.sha256(prompt.encode()).hexdigest()

    def get_summary(
        self, system: list[str] | None = None, prompt: list[str] | None = None
    ) -> str:
        system = system or self.get_summary_chat_system()
        prompt = prompt or self.get_summary_chat_prompt()
        kwargs = {
            key: value
            for key, value in {
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }.items()
            if value is not None
        }
        return MistralService.get_chat_response(system, prompt, **kwargs)


class ProjectEmbedding(MistralEmbedding, HasWeight):
    item = models.OneToOneField(
        "projects.Project", on_delete=models.CASCADE, related_name="embedding"
    )

    def get_weight(self) -> float:
        return self.item.get_or_create_score().score

    @property
    def project(self) -> "Project":
        return self.item

    def get_is_visible(self) -> bool:
        return len(self.project.description) > 10 or self.project.blog_entries.exists()

    @classmethod
    def get_summary_chat_system(cls) -> list[str]:
        return [
            "CONTEXT : You are responsible for the portfolio of projects in your organization.",
            "OBJECTIVE : Generate a project profile from the following information.\
                - First give the project global objective\
                - Then give the project impact\
                - Then give the project summary",
            "STYLE: Easy to understand for an embedding model.",
            "TONE: Concise and explicit.",
            "AUDIENCE : An embedding model which will turn this summary into a vector.",
            "RESPONSE : The response must be a text of 120 words MAXIMUM.",
            "IMPORTANT : DO NOT MAKE UP ANY FACTS, EVEN IF IT MEANS RETURNING JUST A SENTENCE",
        ]

    def get_summary_chat_prompt(self) -> list[str]:
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
        if self.project.tags.exists():
            tags = [tag.title_en or tag.title_fr for tag in self.project.tags.all()]
            tags = [tag for tag in tags if tag]
            key_concepts = ", ".join(tags)
        else:
            key_concepts = ""
        prompt = [
            ("Title", self.project.title),
            ("Purpose", self.project.purpose),
            ("Key concepts", key_concepts),
            ("Content", content),
        ]
        return [f"{key} : {value}" for key, value in prompt if value]


class UserProfileEmbedding(MistralEmbedding, HasWeight):
    item = models.OneToOneField(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        related_name="profile_embedding",
    )

    @property
    def user(self) -> "ProjectUser":
        return self.item

    def get_weight(self) -> float:
        return 2 * self.user.get_or_create_score().score

    def get_is_visible(self) -> bool:
        return (
            len(self.user.description) > 10
            or self.user.skills.filter(level__gte=3).exists()
        )

    @classmethod
    def get_summary_chat_system(cls) -> list[str]:
        return [
            "CONTEXT : You are responsible for the portfolio of people in your organization.",
            "OBJECTIVE : Generate a person's professional profile from the following information.",
            "STYLE: Easy to understand for an embedding model.",
            "TONE: Concise and explicit.",
            "AUDIENCE : An embedding model which will turn this summary into a vector.",
            "RESPONSE : The response must be a text of 120 words MAXIMUM.",
            "IMPORTANT : DO NOT MAKE UP ANY FACTS, EVEN IF IT MEANS RETURNING JUST A SENTENCE",
        ]

    def get_summary_chat_prompt(self) -> list[str]:
        expert_skills = self.user.skills.filter(level=4).values_list(
            "tag__title", flat=True
        )
        expert_skills = ", ".join(expert_skills) if expert_skills else ""
        competent_skills = self.user.skills.filter(level=3).values_list(
            "tag__title", flat=True
        )
        competent_skills = ", ".join(competent_skills) if competent_skills else ""
        description = "\n".join(
            [
                strip_tags(self.user.description)[:10000],
            ]
        )
        prompt = [
            ("Job", self.user.job),
            ("Expert in", expert_skills),
            ("Competent in", competent_skills),
            ("Biography", description),
        ]
        return [f"{key} : {value}" for key, value in prompt if value]


class UserProjectsEmbedding(Embedding, HasWeight):
    item = models.OneToOneField(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        related_name="projects_embedding",
    )

    @property
    def user(self) -> "ProjectUser":
        return self.item

    def get_weight(self) -> float:
        return sum(
            p.get_or_create_score().score
            for p in Project.objects.filter(
                groups__users=self.user,
                deleted_at__isnull=True,
                embedding__isnull=False,
                embedding__is_visible=True,
                embedding__embedding__isnull=False,
            ).distinct()
        )

    def get_is_visible(self) -> bool:
        return self.user.groups.filter(
            projects__isnull=False,
            projects__deleted_at__isnull=True,
            projects__embedding__isnull=False,
            projects__embedding__is_visible=True,
            projects__embedding__embedding__isnull=False,
        ).exists()

    def set_embedding(self, *args, **kwargs) -> "UserProjectsEmbedding":
        data = [
            [
                {
                    "project": group.projects.get(),
                    "weight": weight,
                }
                for group in self.user.groups.filter(
                    projects__isnull=False,
                    projects__deleted_at__isnull=True,
                    projects__embedding__isnull=False,
                    projects__embedding__is_visible=True,
                    projects__embedding__embedding__isnull=False,
                    name__contains=role,
                )
            ]
            for role, weight in [
                (GroupData.Role.MEMBERS, 1),
                (GroupData.Role.OWNERS, 2),
                (GroupData.Role.REVIEWERS, 1),
                (GroupData.Role.MEMBER_GROUPS, 1),
                (GroupData.Role.OWNER_GROUPS, 2),
                (GroupData.Role.REVIEWER_GROUPS, 1),
            ]
        ]
        data = [
            {
                "vector": d["project"].embedding.embedding,
                "weight": d["weight"] * d["project"].get_or_create_score().score,
            }
            for d in list(itertools.chain.from_iterable(data))
            if d["project"].embedding and d["project"].embedding.embedding is not None
        ]
        total_weight = sum(d["weight"] for d in data)
        vectors = [[i * d["weight"] for i in d["vector"]] for d in data]
        self.embedding = [sum(row) / total_weight for row in zip(*vectors)] or None
        self.save()
        return self


class UserEmbedding(Embedding):
    item = models.OneToOneField(
        "accounts.ProjectUser", on_delete=models.CASCADE, related_name="embedding"
    )

    @property
    def user(self) -> "ProjectUser":
        return self.item

    def get_is_visible(self) -> bool:
        profile_embedding, _ = UserProfileEmbedding.objects.get_or_create(
            item=self.user
        )
        projects_embedding, _ = UserProjectsEmbedding.objects.get_or_create(
            item=self.user
        )
        return profile_embedding.get_is_visible() or projects_embedding.get_is_visible()

    def set_embedding(self, *args, **kwargs) -> "UserEmbedding":
        profile_embedding, _ = UserProfileEmbedding.objects.get_or_create(
            item=self.user
        )
        projects_embedding, _ = UserProjectsEmbedding.objects.get_or_create(
            item=self.user
        )
        embeddings = [profile_embedding.vectorize(), projects_embedding.vectorize()]

        total_score = 0
        results = []
        for embedding in embeddings:
            if embedding.embedding is not None:
                score = embedding.get_weight()
                results.append([e * score for e in embedding.embedding])
                total_score += score
        try:
            self.embedding = [sum(row) / total_score for row in zip(*results)] or None
        except ZeroDivisionError:
            self.embedding = None
        self.save()
        return self


class TagEmbedding(MistralEmbedding):
    item = models.OneToOneField(
        "skills.Tag", on_delete=models.CASCADE, related_name="embedding"
    )

    @property
    def tag(self) -> "Tag":
        return self.item

    def get_is_visible(self) -> bool:
        return bool(self.tag.description) or bool(self.tag.title)

    def set_embedding(self, *args, **kwargs) -> "TagEmbedding":
        prompt = [
            self.tag.title,
            self.tag.description,
        ]
        prompt_hashcode = self.hash_prompt(prompt)
        if self.prompt_hashcode != prompt_hashcode:
            prompt = "\n\n".join(prompt)
            self.embedding = MistralService.get_embedding(prompt)
            self.prompt_hashcode = prompt_hashcode
            self.save()
        return self
