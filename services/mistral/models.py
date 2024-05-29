import hashlib
from typing import TYPE_CHECKING, List, Optional

from django.db import models, transaction
from django.db.models import QuerySet
from django.utils.html import strip_tags
from pgvector.django import CosineDistance, VectorField

from apps.projects.models import Project

from .exceptions import VectorSearchWrongQuerysetError
from .interface import MistralService

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser


class Embedding(models.Model):
    """
    Abstract class for models that store an embedding vector for another model.

    To set it up, you need to define the following attributes:
        - item: a OneToOneField to the model that will be embedded, it is advised
            to set an explicit related_name
        - embed_if_not_visible: whether to embed the item if it's not visible in
            vector_search results

    And the following methods:
        - get_is_visible: a method that returns whether the item should be
            returned in vector_search results
        - set_embedding: a method that sets the embedding of the item and returns
            the instance
    """

    item: models.OneToOneField
    embed_if_not_visible: bool = False

    last_update = models.DateTimeField(auto_now=True)
    embedding = VectorField(dimensions=1024, null=True)
    is_visible = models.BooleanField(default=False)

    class Meta:
        abstract = True

    def get_is_visible(self) -> bool:
        raise NotImplementedError()

    def set_embedding(self, summary: Optional[str] = None) -> "Embedding":
        raise NotImplementedError()

    def set_visibility(self) -> bool:
        self.is_visible = self.get_is_visible()
        self.save(update_fields=["is_visible"])
        return self.is_visible

    @transaction.atomic
    def vectorize(self, summary: Optional[str] = None) -> "Embedding":
        if self.set_visibility() or self.embed_if_not_visible:
            return self.set_embedding(summary)
        return self

    @classmethod
    def vector_search(
        cls, embedding: List[float], queryset: Optional[QuerySet] = None
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
        - embed_if_not_visible: whether to embed the item if it's not visible in
            vector_search results
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

    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    summary = models.TextField(blank=True)
    prompt_hashcode = models.CharField(max_length=64, default="")

    class Meta:
        abstract = True

    @classmethod
    def get_summary_chat_system(cls) -> List[str]:
        raise NotImplementedError()

    def get_summary_chat_prompt(self) -> List[str]:
        raise NotImplementedError()

    def set_embedding(self, summary: Optional[str] = None) -> "Embedding":
        prompt = self.get_summary_chat_prompt()
        summary = summary or self.get_summary(prompt=prompt)
        embedding = self.get_embedding(summary)
        self.summary = summary
        self.embedding = embedding
        self.prompt_hashcode = self.hash_prompt(prompt)
        self.save()
        return self

    @transaction.atomic
    def vectorize(self, summary: str | None = None) -> Embedding:
        if self.prompt_hashcode != self.hash_prompt():
            return super().vectorize(summary)
        return self

    def get_embedding(self, summary: Optional[str] = None) -> List[float]:
        summary = summary or self.get_summary()
        return MistralService.get_embedding(summary)

    def hash_prompt(self, prompt: Optional[List[str]] = None) -> str:
        prompt = prompt or self.get_summary_chat_prompt()
        prompt = "\n".join(prompt)
        return hashlib.sha256(prompt.encode()).hexdigest()

    def get_summary(
        self, system: Optional[List[str]] = None, prompt: Optional[List[str]] = None
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


class ProjectEmbedding(MistralEmbedding):
    item = models.OneToOneField(
        "projects.Project", on_delete=models.CASCADE, related_name="embedding"
    )
    embed_if_not_visible = False

    @property
    def project(self) -> "Project":
        return self.item

    def get_is_visible(self) -> bool:
        return len(self.project.description) > 10 or self.project.blog_entries.exists()

    @classmethod
    def get_summary_chat_system(cls) -> List[str]:
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
            tags = [
                tag.name_en or tag.name_fr for tag in self.project.wikipedia_tags.all()
            ]
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


class UserProfileEmbedding(MistralEmbedding):
    item = models.OneToOneField(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        related_name="profile_embedding",
    )
    embed_if_not_visible = True

    @property
    def user(self) -> "ProjectUser":
        return self.item

    def get_is_visible(self) -> bool:
        return (
            len(self.user.personal_description) > 10
            or len(self.user.professional_description) > 10
            or self.user.skills.filter(level__gte=3).exists()
        )

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
        prompt = [
            ("Job", self.user.job),
            ("Expert in", expert_skills),
            ("Competent in", competent_skills),
            ("Biography", description),
        ]
        return [f"{key} : {value}" for key, value in prompt if value]


class UserProjectsEmbedding(Embedding):
    item = models.OneToOneField(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        related_name="projects_embedding",
    )
    embed_if_not_visible = False

    @property
    def user(self) -> "ProjectUser":
        return self.item

    def get_is_visible(self) -> bool:
        return self.user.groups.filter(
            projects__isnull=False,
            projects__embedding__isnull=False,
            projects__embedding__embedding__isnull=False,
        ).exists()

    def set_embedding(self, summary: Optional[str] = None) -> List[float]:
        # Get all the projects the user is a member of
        member_projects = self.user.groups.filter(
            projects__isnull=False,
            projects__deleted_at__isnull=True,
            projects__embedding__isnull=False,
            projects__embedding__embedding__isnull=False,
            name__contains=Project.DefaultGroup.MEMBERS,
        )
        owner_projects = self.user.groups.filter(
            projects__isnull=False,
            projects__deleted_at__isnull=True,
            projects__embedding__isnull=False,
            projects__embedding__embedding__isnull=False,
            name__contains=Project.DefaultGroup.OWNERS,
        )
        reviewer_projects = self.user.groups.filter(
            projects__isnull=False,
            projects__deleted_at__isnull=True,
            projects__embedding__isnull=False,
            projects__embedding__embedding__isnull=False,
            name__contains=Project.DefaultGroup.REVIEWERS,
        )
        group_projects = self.user.groups.filter(
            projects__isnull=False,
            projects__deleted_at__isnull=True,
            projects__embedding__isnull=False,
            projects__embedding__embedding__isnull=False,
            name__contains=Project.DefaultGroup.PEOPLE_GROUPS,
        )

        member_projects = [g.projects.get() for g in member_projects]
        owner_projects = [g.projects.get() for g in owner_projects]
        reviewer_projects = [g.projects.get() for g in reviewer_projects]
        group_projects = [g.projects.get() for g in group_projects]

        # Calculate the weight of each type of project
        member_projects_weight = 1 * len(member_projects)
        owner_projects_weight = 2 * len(owner_projects)
        reviewer_projects_weight = 1 * len(reviewer_projects)
        group_projects_weight = 1 * len(group_projects)
        total_weight = (
            member_projects_weight
            + owner_projects_weight
            + reviewer_projects_weight
            + group_projects_weight
        )

        # Get the embeddings of the projects
        member_projects_embedding = [
            p.embedding.embedding
            for p in member_projects
            if p.embedding and p.embedding.embedding is not None
        ]
        owner_projects_embedding = [
            p.embedding.embedding
            for p in owner_projects
            if p.embedding and p.embedding.embedding is not None
        ]
        reviewer_projects_embedding = [
            p.embedding.embedding
            for p in reviewer_projects
            if p.embedding and p.embedding.embedding is not None
        ]
        group_projects_embedding = [
            p.embedding.embedding
            for p in group_projects
            if p.embedding and p.embedding.embedding is not None
        ]

        # Calculate the average embedding of each type of project
        average_member_projects_embedding = [
            sum(row) / len(row) for row in zip(*member_projects_embedding)
        ]
        average_owner_projects_embedding = [
            sum(row) / len(row) for row in zip(*owner_projects_embedding)
        ]
        average_reviewer_projects_embedding = [
            sum(row) / len(row) for row in zip(*reviewer_projects_embedding)
        ]
        average_group_projects_embedding = [
            sum(row) / len(row) for row in zip(*group_projects_embedding)
        ]

        # Calculate the sum of the weighted average embeddings
        total_embedding = [
            [member_projects_weight * i for i in average_member_projects_embedding],
            [owner_projects_weight * i for i in average_owner_projects_embedding],
            [reviewer_projects_weight * i for i in average_reviewer_projects_embedding],
            [group_projects_weight * i for i in average_group_projects_embedding],
        ]
        total_embedding = [e for e in total_embedding if e != []]

        # Calculate the average embedding of all the user's projects
        self.embedding = [sum(row) / total_weight for row in zip(*total_embedding)]
        self.save()
        return self


class UserEmbedding(Embedding):
    item = models.OneToOneField(
        "accounts.ProjectUser", on_delete=models.CASCADE, related_name="embedding"
    )
    embed_if_not_visible = True

    @property
    def user(self) -> "ProjectUser":
        return self.item

    def get_is_visible(self) -> bool:
        return (
            self.user.projects_embedding.is_visible
            or self.user.profile_embedding.is_visible
        )

    def set_embedding(self, summary: Optional[str] = None) -> List[float]:
        profile_embedding = UserProfileEmbedding.objects.get_or_create(item=self.user)
        projects_embedding = UserProjectsEmbedding.objects.get_or_create(item=self.user)

        profile_embedding = profile_embedding.vectorize()
        projects_embedding = projects_embedding.vectorize()

        embeddings = []
        total_score = 0

        if projects_embedding.is_visible:
            projects = Project.objects.filter(groups__users=self.user)
            projects_scores = [p.calculate_score() for p in projects]
            projects_score = sum(projects_scores)
            embeddings.append(
                [e * projects_score for e in projects_embedding.embedding]
            )
            total_score += projects_score

        if profile_embedding.is_visible:
            profile_score = 2 * self.user.calculate_score()
            embeddings.append([e * profile_score for e in profile_embedding.embedding])
            total_score += profile_score

        self.embedding = [sum(row) / total_score for row in zip(*embeddings)]
        self.save()
        return self
