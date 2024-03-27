from django.db import models

from apps.commons.models import OrganizationRelated
from apps.misc.models import Language


class News(models.Model, OrganizationRelated):
    """News isntance.

    Attributes
    ----------
    ----------
    id: Charfield
        UUID4 used as the model's PK.
    title: CharField
        Title of the news.
    content: TextField
        Content of the news.
    header_image: ForeignKey
        Image in the news.
    publication_date: DateTimeField
        Date of teh news' publication.
    groups: ManyToManyField
        Groups which have access to the news.
    created_at: DateTimeField
        Date of creation of this project.
    updated_at: DateTimeField
        Date of the last change made to the project.
    """

    title = models.CharField(max_length=255, verbose_name=("title"))
    content = models.TextField(blank=True, default="")
    header_image = models.ForeignKey(
        "files.Image",
        on_delete=models.SET_NULL,
        null=True,
        related_name="news_header",
    )
    publication_date = models.DateTimeField()
    people_groups = models.ManyToManyField("accounts.PeopleGroup", related_name="news")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    language = models.CharField(
        max_length=2, choices=Language.choices, default=Language.default()
    )
    organizations = models.ManyToManyField(
        "organizations.Organization", related_name="news"
    )
