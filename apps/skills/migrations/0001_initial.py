# Generated by Django 4.2.15 on 2024-10-01 13:13

import apps.commons.mixins
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("organizations", "0012_alter_organization_options"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Tag",
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
                    "type",
                    models.CharField(
                        choices=[
                            ("wikipedia", "Wikipedia"),
                            ("esco", "Esco"),
                            ("custom", "Custom"),
                        ],
                        default="custom",
                        max_length=255,
                    ),
                ),
                (
                    "secondary_type",
                    models.CharField(
                        choices=[("skill", "Skill"), ("occupation", "Occupation"), ("tag", "Tag")],
                        default="tag",
                        max_length=255,
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("title_en", models.CharField(max_length=255, null=True)),
                ("title_fr", models.CharField(max_length=255, null=True)),
                ("description", models.TextField(blank=True)),
                ("description_en", models.TextField(blank=True, null=True)),
                ("description_fr", models.TextField(blank=True, null=True)),
                ("external_id", models.CharField(max_length=2048, unique=True)),
                (
                    "organization",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="custom_tags",
                        to="organizations.organization",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="TagClassification",
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
                    "type",
                    models.CharField(
                        choices=[
                            ("wikipedia", "Wikipedia"),
                            ("esco", "Esco"),
                            ("custom", "Custom"),
                        ],
                        default="custom",
                        max_length=255,
                    ),
                ),
                ("slug", models.SlugField(unique=True)),
                ("is_public", models.BooleanField(default=False)),
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                (
                    "tags",
                    models.ManyToManyField(
                        related_name="tag_classifications", to="skills.tag"
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="tag_classifications",
                        to="organizations.organization",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Skill",
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
                    "type",
                    models.CharField(
                        choices=[("skill", "Skill"), ("hobby", "Hobby")],
                        default="skill",
                        max_length=8,
                    ),
                ),
                ("level", models.SmallIntegerField()),
                ("level_to_reach", models.SmallIntegerField()),
                ("category", models.CharField(blank=True, default="", max_length=255)),
                ("can_mentor", models.BooleanField(default=False)),
                ("needs_mentor", models.BooleanField(default=False)),
                ("comment", models.TextField(blank=True, default="")),
                (
                    "tag",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="skills",
                        to="skills.tag",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="skills",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            bases=(models.Model, apps.commons.mixins.HasOwner),
        ),
    ]
