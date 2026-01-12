import uuid

from django import forms
from django.contrib import admin
from django.db import models

from apps.commons.admin import TranslateObjectAdminMixin

from .models import Image, ProjectUserAttachmentFile, ProjectUserAttachmentLink


class ImageForm(forms.ModelForm):
    class ImageUploadToChoices(models.TextChoices):
        USER_PROFILE = "account/profile/"
        ORGANIZATION_LOGO = "organization/logo/"
        ORGANIZATION_BANNER = "organization/banner/"
        ORGANIZATION_IMAGES = "organization/images/"
        CATEGORY_BACKGROUND = "category/background/"
        TEMPLATE_IMAGES = "template/images/"
        GROUP_HEADER = "people_group/header/"
        GROUP_LOGO = "people_group/logo/"
        PROJECT_HEADER = "project/header/"
        PROJECT_IMAGES = "project/images/"
        BLOG_ENTRY_IMAGES = "blog_entry/images/"
        COMMENT_IMAGES = "comment/images/"
        PROJECT_TAB_IMAGES = "project_tabs/images/"
        PROJECT_TAB_ITEM_IMAGES = "project_tab_items/images/"
        PROJECT_MESSAGE_IMAGES = "project_messages/images/"
        NEWS_HEADER = "news/header/"
        NEWS_IMAGES = "news/images/"
        INSTRUCTION_IMAGES = "instructions/images/"
        EVENT_IMAGES = "events/images/"
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
        upload_to = self.cleaned_data.get("upload_to")
        self.instance._upload_to = self.get_upload_to(upload_to)
        return super(ImageForm, self).save(commit=commit)

    class Meta:
        model = Image
        fields = "__all__"


@admin.register(Image)
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


@admin.register(ProjectUserAttachmentFile)
class ProjectUserAttachmentFileAdmin(TranslateObjectAdminMixin, admin.ModelAdmin):
    list_display = ("id", "owner", "title")
    autocomplete_fields = ("owner",)
    search_fields = ("owner", "title", "mime")


@admin.register(ProjectUserAttachmentLink)
class ProjectUserAttachmentLinkAdmin(TranslateObjectAdminMixin, admin.ModelAdmin):
    list_display = ("id", "owner", "title", "site_url")
    autocomplete_fields = ("owner",)
    search_fields = ("owner", "title", "stie_url")
