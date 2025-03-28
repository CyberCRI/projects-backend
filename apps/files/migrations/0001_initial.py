# Generated by Django 4.2.7 on 2024-01-05 17:16

import apps.commons.mixins
import apps.files.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models
import stdimage.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AttachmentFile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "attachment_type",
                    models.CharField(
                        choices=[
                            ("file", "File"),
                            ("image", "Image"),
                            ("video", "Video"),
                            ("link", "Link"),
                        ],
                        default="file",
                        max_length=10,
                    ),
                ),
                (
                    "file",
                    models.FileField(
                        upload_to=apps.files.models.attachment_directory_path
                    ),
                ),
                ("mime", models.CharField(max_length=100)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("hashcode", models.CharField(default="", max_length=64)),
            ],
            bases=(
                models.Model,
                apps.commons.mixins.ProjectRelated,
                apps.commons.mixins.OrganizationRelated,
            ),
        ),
        migrations.CreateModel(
            name="AttachmentLink",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "attachment_type",
                    models.CharField(
                        choices=[
                            ("file", "File"),
                            ("image", "Image"),
                            ("video", "Video"),
                            ("link", "Link"),
                        ],
                        default="link",
                        max_length=10,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("project_website", "Project Website"),
                            ("documentary_resource", "Documentary Resource"),
                            ("inspiration", "Inspiration"),
                            ("data", "Data"),
                            ("publication", "Publication"),
                            ("source_code", "Source Code"),
                            ("tool", "Tool"),
                            ("other", "Other"),
                        ],
                        default="other",
                        max_length=50,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                (
                    "preview_image_url",
                    models.URLField(
                        help_text="attachment link preview image, mostly thumbnails",
                        max_length=2048,
                    ),
                ),
                ("site_name", models.CharField(max_length=255)),
                ("site_url", models.URLField(max_length=2048)),
                ("title", models.CharField(blank=True, max_length=255)),
            ],
            bases=(
                models.Model,
                apps.commons.mixins.ProjectRelated,
                apps.commons.mixins.OrganizationRelated,
            ),
        ),
        migrations.CreateModel(
            name="HistoricalAttachmentFile",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                (
                    "attachment_type",
                    models.CharField(
                        choices=[
                            ("file", "File"),
                            ("image", "Image"),
                            ("video", "Video"),
                            ("link", "Link"),
                        ],
                        default="file",
                        max_length=10,
                    ),
                ),
                ("file", models.TextField(max_length=100)),
                ("mime", models.CharField(max_length=100)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                ("hashcode", models.CharField(default="", max_length=64)),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical attachment file",
                "verbose_name_plural": "historical attachment files",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="PeopleResource",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("people_id", models.CharField(max_length=255)),
                ("people_data", models.JSONField(default=dict)),
            ],
        ),
        migrations.CreateModel(
            name="Image",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                (
                    "file",
                    stdimage.models.StdImageField(
                        force_min_size=False,
                        height_field="height",
                        upload_to=apps.files.models.dynamic_upload_to,
                        variations={
                            "full": (1920, 10000),
                            "large": (1024, 10000),
                            "medium": (768, 10000),
                            "small": (500, 10000),
                        },
                        width_field="width",
                    ),
                ),
                ("height", models.IntegerField(blank=True, null=True)),
                ("width", models.IntegerField(blank=True, null=True)),
                ("natural_ratio", models.FloatField(blank=True, null=True)),
                ("scale_x", models.FloatField(blank=True, null=True)),
                ("scale_y", models.FloatField(blank=True, null=True)),
                ("left", models.FloatField(blank=True, null=True)),
                ("top", models.FloatField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "owner",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="images",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            bases=(
                models.Model,
                apps.commons.mixins.HasOwner,
                apps.commons.mixins.OrganizationRelated,
                apps.commons.mixins.ProjectRelated,
            ),
        ),
        migrations.CreateModel(
            name="HistoricalAttachmentLink",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                (
                    "attachment_type",
                    models.CharField(
                        choices=[
                            ("file", "File"),
                            ("image", "Image"),
                            ("video", "Video"),
                            ("link", "Link"),
                        ],
                        default="link",
                        max_length=10,
                    ),
                ),
                (
                    "category",
                    models.CharField(
                        choices=[
                            ("project_website", "Project Website"),
                            ("documentary_resource", "Documentary Resource"),
                            ("inspiration", "Inspiration"),
                            ("data", "Data"),
                            ("publication", "Publication"),
                            ("source_code", "Source Code"),
                            ("tool", "Tool"),
                            ("other", "Other"),
                        ],
                        default="other",
                        max_length=50,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                (
                    "preview_image_url",
                    models.URLField(
                        help_text="attachment link preview image, mostly thumbnails",
                        max_length=2048,
                    ),
                ),
                ("site_name", models.CharField(max_length=255)),
                ("site_url", models.URLField(max_length=2048)),
                ("title", models.CharField(blank=True, max_length=255)),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "historical attachment link",
                "verbose_name_plural": "historical attachment links",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
    ]
