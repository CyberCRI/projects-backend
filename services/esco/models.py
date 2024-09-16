from django.db import models


class EscoUpdateError(models.Model):
    """
    Model to store errors that occurred during the update of Esco data.
    """

    item_type = models.CharField(max_length=255)
    item_id = models.CharField(max_length=255)
    error = models.CharField(max_length=255)
    traceback = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Error for {self.item_type} {self.item_id}: {self.error}"


class EscoSkill(models.Model):
    uri = models.URLField(max_length=2048, unique=True)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    parents = models.ManyToManyField("self", blank=True)
    essential_skills = models.ManyToManyField(
        "self", related_name="essential_for_skills", symmetrical=False, blank=True
    )
    optional_skills = models.ManyToManyField(
        "self", related_name="optional_for_skills", symmetrical=False, blank=True
    )

    def __str__(self):
        return f"EscoSkill: {self.title}"


class EscoOccupation(models.Model):
    uri = models.URLField(max_length=2048, unique=True)
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    parents = models.ManyToManyField("self", blank=True)
    essential_skills = models.ManyToManyField(
        "esco.EscoSkill", related_name="essential_for_occupations", blank=True
    )
    optional_skills = models.ManyToManyField(
        "esco.EscoSkill", related_name="optional_for_occupations", blank=True
    )

    def __str__(self):
        return f"EscoOccupation: {self.title}"
