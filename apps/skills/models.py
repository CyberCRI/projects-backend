from typing import TYPE_CHECKING, Any

from django.db import models
from django.utils.text import slugify

from apps.commons.models import HasMultipleIDs, HasOwner, OrganizationRelated

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

        WIKIPEDIA = "wikipedia"
        ESCO = "esco"
        CUSTOM = "custom"

    class SecondaryTagType(models.TextChoices):
        """Secondary type of a tag,"""

        SKILL = "skill"
        OCCUPATION = "occupation"

    type = models.CharField(
        max_length=255, choices=TagType.choices, default=TagType.CUSTOM.value
    )
    secondary_type = models.CharField(
        max_length=255, choices=SecondaryTagType.choices, blank=True
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.SET_NULL,
        null=True,
        related_name="custom_tags",
    )
    external_id = models.CharField(max_length=2048, unique=True)

    def __str__(self):
        return f"{self.type.capitalize()} Tag - {self.title}"

    def get_related_organizations(self):
        """Return the organizations related to this model."""
        if self.type == self.TagType.CUSTOM:
            return [self.organization]
        return []


class TagClassification(models.Model, HasMultipleIDs, OrganizationRelated):
    """
    Subset of tags that can be used as Skills, Hobbies or Project tags.
    Users are allowed to create their own tags and classifications.
    """

    class TagClassificationType(models.TextChoices):
        """Main type of a tag."""

        WIKIPEDIA = "wikipedia"
        ESCO = "esco"
        CUSTOM = "custom"

    slug = models.SlugField(unique=True)
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
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    tags = models.ManyToManyField("skills.Tag", related_name="tag_classifications")

    def __str__(self):
        return f"Tags classification - {self.title}"

    def get_related_organizations(self):
        """Return the organizations related to this model."""
        if self.type == self.TagClassificationType.CUSTOM:
            return [self.organization]
        return []

    def get_slug(self) -> str:
        if self.slug == "":
            title = self.title
            if title == "":
                title = "tag-classification"
            raw_slug = slugify(title[0:46])
            try:
                int(raw_slug)
                raw_slug = f"tag-classification-{raw_slug}"  # Prevent clashes with IDs
            except ValueError:
                pass
            slug = raw_slug
            same_slug_count = 0
            while TagClassification.objects.filter(slug=slug).exists():
                same_slug_count += 1
                slug = f"{raw_slug}-{same_slug_count}"
            return slug
        return self.slug

    @classmethod
    def get_id_field_name(cls, object_id: Any) -> str:
        """Get the name of the field which contains the given ID."""
        try:
            int(object_id)
            return "id"
        except ValueError:
            return "slug"

    @classmethod
    def get_or_create_wikipedia_classification(cls):
        classification, _ = cls.objects.get_or_create(
            type=cls.TagClassificationType.WIKIPEDIA,
            defaults={
                "title": cls.TagClassificationType.WIKIPEDIA.capitalize(),
                "is_public": True,
            },
        )
        return classification

    @classmethod
    def get_or_create_esco_classification(cls):
        classification, _ = cls.objects.get_or_create(
            type=cls.TagClassificationType.ESCO,
            defaults={
                "title": cls.TagClassificationType.ESCO.capitalize(),
                "is_public": True,
            },
        )
        return classification


class Skill(models.Model, HasOwner):
    class SkillType(models.TextChoices):
        """Visibility setting of a project."""

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
