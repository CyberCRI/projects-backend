import datetime
import uuid
from typing import TYPE_CHECKING, Any, List, Optional

from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import ForeignObjectRel, QuerySet
from django.utils import timezone

from apps.commons.mixins import HasMultipleIDs, HasOwner, HasOwners, OrganizationRelated
from services.translator.mixins import HasAutoTranslatedFields

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser


class Tag(models.Model, OrganizationRelated):
    """
    Tag model to store tags from different sources.
    Current sources are :
    - Wikipedia : tags are retrieved from the wikidata API when the user creates a tag
    - ESCO : tags come from the ESCO API and are updated automatically by the system
    - Custom : tags created by the administrators

    Tags are used to create skills and hobbies for users, and to classify projects.

    Attributes
    ----------
    type: Charfield
        The source of the tag.
    secondary_type: Charfield
        The type of the tag, it can be used when the source has types that are handled differently.
    title: Charfield
        The title of the tag, it is a translated field and should be stored in multiple languages.
    description: TextField
        The description of the tag, it is a translated field and should be stored in multiple languages.
    organization: ForeignKey
        The organization that created the tag. It is only used for custom tags.
    external_id: Charfield
        The ID of the tag in the external source. For custum tags, we use a UUID.
    """

    class TagType(models.TextChoices):
        """Main type of a tag."""

        WIKIPEDIA = "Wikipedia"
        ESCO = "ESCO"
        CUSTOM = "Custom"

    class SecondaryTagType(models.TextChoices):
        """Secondary type of a tag,"""

        SKILL = "skill"
        OCCUPATION = "occupation"
        TAG = "tag"

    type = models.CharField(
        max_length=255, choices=TagType.choices, default=TagType.CUSTOM.value
    )
    secondary_type = models.CharField(
        max_length=255,
        choices=SecondaryTagType.choices,
        default=SecondaryTagType.TAG.value,
    )
    title = models.CharField(max_length=255)
    alternative_titles = models.TextField(blank=True)
    description = models.TextField(blank=True)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        related_name="custom_tags",
    )
    external_id = models.CharField(max_length=2048, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.type.capitalize()} Tag - {self.title}"

    def save(
        self, force_insert=False, force_update=False, using=None, update_fields=None
    ):
        """
        For custom tags, we generate a random UUID as the external ID.
        This prevents IntegrityError because the external ID is supposed to be unique.
        """
        if not self.external_id:
            self.external_id = str(uuid.uuid4())
        return super().save(force_insert, force_update, using, update_fields)

    def get_related_organizations(self):
        """Return the organizations related to this model."""
        if self.type == self.TagType.CUSTOM:
            return [self.organization]
        return []

    @classmethod
    def get_orphan_tags(
        cls, threshold: Optional[int] = None, **filters
    ) -> QuerySet["Tag"]:
        """Return a QuerySet containing all the orphan tags.

        Parameters
        ----------
        threshold: int, optional
            Time (in seconds) after which a tag is considered an orphan if it
            was not assigned to any model. Default to
            `settings.TAG_ORPHAN_THRESHOLD_SECONDS`.
        """
        if threshold is None:
            threshold = settings.TAG_ORPHAN_THRESHOLD_SECONDS
        filters = {
            **{
                f"{f.name}__isnull": True
                for f in cls._meta.get_fields()
                if isinstance(f, ForeignObjectRel)
                and f.name not in ["tag_classifications", "embedding"]
            },
            **filters,
        }
        threshold = timezone.localtime(timezone.now()) - datetime.timedelta(
            seconds=threshold
        )
        return cls.objects.filter(created_at__lt=threshold, **filters)


class TagClassification(
    HasAutoTranslatedFields,
    HasMultipleIDs,
    OrganizationRelated,
    models.Model,
):
    """
    Subset of tags that can be used as Skills, Hobbies or Project tags.
    Users are allowed to create their own tags and classifications.
    """

    auto_translated_fields: List[str] = ["title", "description"]
    slugified_fields: List[str] = ["title"]
    slug_prefix: str = "tag-classification"
    reserved_slugs = ["enabled-for-projects", "enabled-for-skills"]

    class TagClassificationType(models.TextChoices):
        """Main type of a tag."""

        WIKIPEDIA = "Wikipedia"
        ESCO = "ESCO"
        CUSTOM = "Custom"

    type = models.CharField(
        max_length=255,
        choices=TagClassificationType.choices,
        default=TagClassificationType.CUSTOM.value,
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        related_name="tag_classifications",
    )
    is_public = models.BooleanField(default=False)
    title = models.CharField(max_length=50)
    slug = models.SlugField(unique=True)
    outdated_slugs = ArrayField(models.SlugField(), default=list)
    description = models.CharField(blank=True, max_length=500)
    tags = models.ManyToManyField("skills.Tag", related_name="tag_classifications")

    def __str__(self):
        return f"Tags classification - {self.title}"

    def get_related_organizations(self):
        """Return the organizations related to this model."""
        if self.type == self.TagClassificationType.CUSTOM:
            return [self.organization]
        return []

    @classmethod
    def get_id_field_name(cls, object_id: Any) -> str:
        """Get the name of the field which contains the given ID."""
        try:
            int(object_id)
            return "id"
        except ValueError:
            return "slug"

    @classmethod
    def get_or_create_default_classification(
        cls, classification_type: str
    ) -> "TagClassification":
        if (
            classification_type not in cls.TagClassificationType.values
            or classification_type == cls.TagClassificationType.CUSTOM
        ):
            raise ValueError("Invalid classification type")
        classification, _ = cls.objects.get_or_create(
            type=classification_type,
            defaults={
                "title": classification_type,
                "is_public": True,
            },
        )
        return classification


class Skill(models.Model, HasOwner):
    class SkillType(models.TextChoices):
        """Main type of a skill."""

        SKILL = "skill"
        HOBBY = "hobby"

    user = models.ForeignKey(
        "accounts.ProjectUser", on_delete=models.CASCADE, related_name="skills"
    )
    type = models.CharField(
        max_length=8, choices=SkillType.choices, default=SkillType.SKILL.value
    )
    tag = models.ForeignKey(
        "skills.Tag", on_delete=models.CASCADE, related_name="skills"
    )
    level = models.SmallIntegerField()
    level_to_reach = models.SmallIntegerField()
    category = models.CharField(max_length=255, blank=True, default="")
    can_mentor = models.BooleanField(default=False)
    needs_mentor = models.BooleanField(default=False)
    comment = models.TextField(blank=True, default="")

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        return self.user == user

    def get_owner(self):
        """Get the owner of the object."""
        return self.user


class Mentoring(models.Model, HasOwners, OrganizationRelated):
    class MentoringStatus(models.TextChoices):
        """Status of a mentoring request."""

        PENDING = "pending"
        ACCEPTED = "accepted"
        REJECTED = "rejected"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="mentorings",
    )
    mentor = models.ForeignKey(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        related_name="mentor_mentorings",
    )
    mentoree = models.ForeignKey(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        related_name="mentoree_mentorings",
    )
    skill = models.ForeignKey(
        "skills.Skill", on_delete=models.CASCADE, related_name="mentorings"
    )
    status = models.CharField(
        max_length=8,
        choices=MentoringStatus.choices,
        null=True,
    )
    created_by = models.ForeignKey(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        related_name="created_mentorings",
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            "mentor",
            "mentoree",
            "skill",
        )

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is an owner of the object."""
        return user in self.get_owners()

    def get_owners(self) -> List["ProjectUser"]:
        """
        Get the owners of the object.

        The HasOwner mixin was meant to be used for models with a single owner.
        In this case, the owner can be either the mentor or the mentoree.
        """
        return [self.mentor, self.mentoree]

    def get_related_organizations(self):
        return [self.organization]


class MentoringMessage(
    HasAutoTranslatedFields, HasOwner, OrganizationRelated, models.Model
):
    """
    Message sent in a mentoring conversation.

    Attributes
    ----------
    mentoring: ForeignKey
        The mentoring conversation the message belongs to.
    sender: ForeignKey
        The user who sent the message.
    content: TextField
        The content of the message.
    created_at: DateTimeField
        The date and time the message was created.
    """

    auto_translated_fields: List[str] = ["content"]

    mentoring = models.ForeignKey(
        "skills.Mentoring", on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        related_name="sent_mentoring_messages",
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def get_related_organizations(self):
        return [self.mentoring.organization]

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        return user == self.sender

    def get_owner(self):
        """Get the owner of the object."""
        return self.sender
