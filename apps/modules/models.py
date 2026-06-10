from django.contrib.contenttypes.fields import (
    GenericForeignKey,
    GenericRelation,
)
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.text import camel_case_to_spaces
from lib.models import DateModelMixins
from services.translator.mixins import HasAutoTranslatedFields


def model_to_str(model: type[models.Model] | str) -> str:
    if isinstance(model, str):
        return str(model)
    return str(model.__name__)


def reverse_relation(
    object: type[models.Model] | str,
    relation: type[models.Model] | str,
    related_query_name: str | None = None,
) -> GenericRelation:
    # auto convert relations from models
    if related_query_name is None:
        relation_name = camel_case_to_spaces(model_to_str(relation))
        related_query_name = f"{relation_name}s"

    return GenericRelation(
        model_to_str(object),
        content_type_field="object_content_type",
        object_id_field="object_id",
        related_query_name=related_query_name,
    )


class Tab(DateModelMixins, HasAutoTranslatedFields, models.Model):
    """A abstract tab

    Attributes
    ----------
    project: ForeignKey
        Project this tab belong to.
    type: CharField
        Type of the tab. Can be either "text" or "blog".
    title: CharField
        Title of the tab.
    description: TextField
        Description of the tab.
    """

    auto_translated_fields: list[str] = ["title", "html:description"]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    icon = models.CharField(max_length=255, blank=True, null=True)
    images = models.ManyToManyField("files.Image", related_name="tabs")

    object_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="object_content_type",
        null=True,
        blank=True,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    object_relation = reverse_relation("Tab", "Tab")
    object = GenericForeignKey("object_content_type", "object_id")

    class Meta:
        abstract = True

    @classmethod
    def create_relation(
        cls, relation: type[models.Model] | str, related_query_name: str | None = None
    ) -> GenericRelation:
        # auto convert relations from models
        return reverse_relation(cls, relation, related_query_name)


class TabItem(DateModelMixins, HasAutoTranslatedFields, models.Model):
    """An item in a abstract tab.

    Attributes
    ----------
    project: ForeignKey
        Project this item belong to.
    title: CharField
        Title of the item.
    content: TextField
        Content of the item.
    """

    tab = models.ForeignKey(Tab, on_delete=models.CASCADE, related_name="items")

    object_content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        related_name="object_content_type",
        null=True,
        blank=True,
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    object_relation = reverse_relation("TabItem", "TabItem")
    object = GenericForeignKey("object_content_type", "object_id")

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.tab.title} - {self.object}"

    @classmethod
    def create_relation(
        cls, relation: type[models.Model] | str, related_query_name: str | None = None
    ) -> GenericRelation:
        # auto convert relations from models
        return reverse_relation(cls, relation, related_query_name)
