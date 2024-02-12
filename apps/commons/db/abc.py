from typing import TYPE_CHECKING, Any, List, Optional

from django.db import models
from django.shortcuts import get_object_or_404
from django.utils import timezone
from pgvector.django import CosineDistance, VectorField

from services.mistral.interface import MistralService

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser
    from apps.organizations.models import Organization
    from apps.projects.models import Project


class OrganizationRelated:
    """Abstract class for models related to an `Organization`."""

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        raise NotImplementedError()


class ProjectRelated:
    """Abstract class for models related to `Project`."""

    def get_related_projects(self) -> List["Project"]:
        """Return the projects related to this model."""
        raise NotImplementedError()


class HasOwner:
    """Abstract class for models which have an owner."""

    def get_owner(self):
        """Get the owner of the object."""
        raise NotImplementedError()

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        raise NotImplementedError()


class PermissionsSetupModel(models.Model):
    """Abstract class for models which should be initialized with permissions."""

    permissions_up_to_date = models.BooleanField(default=False)

    def setup_permissions(self, user: Optional["ProjectUser"] = None):
        """Initialize permissions for the instance."""
        raise NotImplementedError()

    def remove_duplicated_roles(self):
        """Remove duplicated roles in the instance."""
        raise NotImplementedError()

    class Meta:
        abstract = True


class HasMultipleIDs:
    """Abstract class for models which have multiple IDs."""

    @classmethod
    def get_id_field_name(cls, object_id: Any) -> str:
        """Get the name of the field which contains the given ID."""
        raise NotImplementedError()

    @classmethod
    def get_main_id(cls, object_id: Any, returned_field: str = "id") -> Any:
        """Get the main ID from a secondary ID."""
        field_name = cls.get_id_field_name(object_id)
        if field_name == returned_field:
            return object_id
        obj = get_object_or_404(cls, **{field_name: object_id})
        return getattr(obj, returned_field)

    @classmethod
    def get_main_ids(
        cls, objects_ids: List[Any], returned_field: str = "id"
    ) -> List[Any]:
        """Get the main IDs from a list of secondary IDs."""
        return [cls.get_main_id(object_id, returned_field) for object_id in objects_ids]


class VectorModel(models.Model):
    last_embedding_update = models.DateTimeField(null=True)
    embedding_summary = models.TextField(blank=True)
    embedding = VectorField(dimensions=1024, null=True)

    @property
    def should_embed(self) -> bool:
        raise NotImplementedError()

    @classmethod
    def get_embedding_summary_chat_system(cls) -> List[str]:
        raise NotImplementedError()

    def get_embedding_summary_prompt(self) -> List[str]:
        raise NotImplementedError()

    def get_embedding_summary(self, **kwargs) -> str:
        system = self.get_embedding_summary_chat_system()
        prompt = self.get_embedding_summary_prompt()
        return MistralService.get_chat_response(system, prompt, **kwargs)

    def get_embedding(self, summary: Optional[str] = None, **kwargs) -> List[float]:
        summary = summary or self.get_embedding_summary(**kwargs)
        return MistralService.get_embedding(summary)

    def vectorize(self, summary: Optional[str] = None, **kwargs) -> "VectorModel":
        if self.should_embed:
            summary = summary or self.get_embedding_summary(**kwargs)
            embedding = self.get_embedding(summary)
            instance = self.__class__.objects.filter(pk=self.pk)
            instance.update(
                embedding_summary=summary,
                embedding=embedding,
                last_embedding_update=timezone.now(),
            )
            return instance.get()
        return self

    @classmethod
    def vector_search(
        cls, embedding: List[float], limit: int = 5
    ) -> List["VectorModel"]:
        return cls.objects.filter(embedding_summary__isnull=False).order_by(
            CosineDistance("embedding", embedding)
        )[:limit]

    class Meta:
        abstract = True
