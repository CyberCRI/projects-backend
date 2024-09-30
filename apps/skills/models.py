from typing import TYPE_CHECKING

from django.db import models

from apps.commons.models import HasOwner

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser


class Tag(models.Model):
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
        related_name="tags_v2",
    )
    external_id = models.CharField(max_length=2048, unique=True)

    def __str__(self):
        return f"{self.type.capitalize()} Tag - {self.title}"

    # @classmethod
    # def type_search(cls, tag_type: str, query: str, language: str = "en", limit: int = 100, offset: int = 0):
    #     if tag_type not in cls.TagType.values:
    #         raise ValueError(f"Invalid type for Tag type_search : {tag_type}")
    #     if hasattr(cls, f"{tag_type}_search"):
    #         return getattr(cls, f"{tag_type}_search")(query, language, limit, offset)
    #     return cls.objects.filter(
    #         Q(type=tag_type),
    #         Q(**{f"title_{language}__icontains": query})
    #         | Q(**{f"description_{language}__icontains": query})
    #     )[offset:offset + limit]

    # @classmethod
    # def wikipedia_search(cls, query: str, language: str = "en", limit: int = 100, offset: int = 0):
    #     response = WikipediaService.search(query, language, limit, offset)
    #     tags = cls.objects.bulk_create(
    #         [
    #             cls(
    #                 **{
    #                     "type": cls.TagType.WIKIPEDIA,
    #                     f"title_{language}": item.get("name", ""),
    #                     f"description_{language}": item.get("description", ""),
    #                     "external_id": item.get("wikipedia_qid", ""),
    #                 }
    #             )
    #             for item in response["results"]
    #         ],
    #         update_conflicts=True,
    #         unique_fields=["external_id"],
    #         update_fields=[f"title_{language}", f"description_{language}"]
    #     )


class TagClassification(models.Model):
    """
    Subset of tags that can be used as Skills, Hobbies or Project tags.
    Users are allowed to create their own tags and classifications.

    """

    is_public = models.BooleanField(default=False)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    tags = models.ManyToManyField("skills.Tag", related_name="classifications")

    def __str__(self):
        return f"Tags classification - {self.title}"


class Skill(models.Model, HasOwner):
    class SkillType(models.TextChoices):
        """Visibility setting of a project."""

        SKILL = "skill"
        HOBBY = "hobby"

    user = models.ForeignKey(
        "accounts.ProjectUser", on_delete=models.CASCADE, related_name="skills_v2"
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
