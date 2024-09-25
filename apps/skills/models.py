from typing import TYPE_CHECKING

from django.db import models

from apps.commons.models import HasOwner

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser


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
    wikipedia_tag = models.ForeignKey(
        "misc.WikipediaTag", on_delete=models.CASCADE, related_name="skills_v2"
    )
    esco_tag = models.ForeignKey(
        "esco.EscoTag", on_delete=models.CASCADE, related_name="skills_v2"
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

    class Meta:
        abstract = True
