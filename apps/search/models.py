from django.db import models


class SearchObject(models.Model):
    """
    SearchObject instance to store objects that can be searched.
    Several types of objects can be stored in this model.

    Attributes
    ----------
    ----------
    project: ForeignKey
        Project instance.
    people_group: ForeignKey
        PeopleGroup instance.
    user: ForeignKey
        ProjectUser instance.
    type: CharField
        Type of the object.
    """

    class SearchObjectType(models.TextChoices):
        """"""

        PROJECT = "project"
        PEOPLE_GROUP = "people_group"
        USER = "user"

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        related_name="search_object",
    )
    people_group = models.ForeignKey(
        "accounts.PeopleGroup",
        on_delete=models.CASCADE,
        null=True,
        related_name="search_object",
    )
    user = models.ForeignKey(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        null=True,
        related_name="search_object",
    )
    type = models.CharField(max_length=50, choices=SearchObjectType.choices)
    last_update = models.DateTimeField(null=True)

    class Meta:
        unique_together = (("type", "user", "project", "people_group"),)

    @property
    def item(self):
        match self.type:
            case self.SearchObjectType.PROJECT:
                return self.project
            case self.SearchObjectType.PEOPLE_GROUP:
                return self.people_group
            case self.SearchObjectType.USER:
                return self.user
        return None

    def __str__(self):
        return f"{self.type} - {self.item}"
