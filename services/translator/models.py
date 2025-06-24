from django.contrib.contenttypes.models import ContentType
from django.db import models


class AutoTranslatedField(models.Model):
    """
    Model to manage automatic translations for various content types.

    Attributes:
    ----------
        content_type: ForeignKey
            The content type of the related instance.
        object_id: CharField
            The ID of the related instance.
        field_name: CharField
            The name of the field to be translated.
        up_to_date: BooleanField
            Indicates if the translation is up to date.
        html_field: BooleanField
            Indicates if the field is an HTML field or a plain text field.
        is_active: BooleanField
            Indicates if the translation is activated for the field.
    """

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=255)
    field_name = models.CharField(max_length=255)
    up_to_date = models.BooleanField(default=False)
    html_field = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("content_type", "object_id", "field_name")

    @property
    def instance(self) -> models.Model:
        """Return the related instance."""
        return self.content_type.get_object_for_this_type(pk=self.object_id)
