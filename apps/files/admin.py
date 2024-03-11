import uuid

from django import forms
from django.contrib import admin
from django.db import models

from .models import Image


class ImageForm(forms.ModelForm):
    class ImageUploadToChoices(models.TextChoices):
        PROJECT_HEADER = "project/header/"
        PROJECT_IMAGES = "project/images/"
        BLOG_ENTRY_IMAGES = "blog_entry/images/"
        COMMENT_IMAGES = "comment/images/"
        ORGANIZATION_LOGO = "organization/logo/"
        ORGANIZATION_BANNER = "organization/banner/"
        ORGANIZATION_IMAGES = "organization/images/"
        FAQ_IMAGES = "faq/images/"
        CATEGORY_BACKGROUND = "category/background/"
        TEMPLATE_IMAGES = "template/images/"
        EMAIL_IMAGES = "email/images/"
        IDP_LOGO = "idp/logo/"

    upload_to = forms.CharField(
        widget=forms.Select(choices=ImageUploadToChoices.choices)
    )

    def get_upload_to(self, path):
        def _inner(instance, filename) -> str:
            return f"{path}{uuid.uuid4()}#{instance.name}"

        return _inner

    def save(self, commit=True):
        upload_to = self.cleaned_data.get("upload_to", None)
        self.instance._upload_to = self.get_upload_to(upload_to)
        return super(ImageForm, self).save(commit=commit)

    class Meta:
        model = Image
        fields = "__all__"


class ImageAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "file",
        "owner",
        "created_at",
    )
    autocomplete_fields = ("owner",)
    form = ImageForm


admin.site.register(Image, ImageAdmin)
