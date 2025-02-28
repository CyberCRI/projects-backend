# Generated by Django 4.2.11 on 2024-04-12 10:01

import apps.commons.mixins
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0004_remove_peoplegroup_type"),
        ("organizations", "0006_alter_organization_options"),
        ("newsfeed", "0003_event"),
    ]

    operations = [
        migrations.CreateModel(
            name="Instruction",
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
                ("title", models.CharField(max_length=255, verbose_name="title")),
                ("content", models.TextField(blank=True, default="")),
                ("publication_date", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "language",
                    models.CharField(
                        choices=[("fr", "French"), ("en", "English")],
                        default="en",
                        max_length=2,
                    ),
                ),
                ("has_to_be_notified", models.BooleanField(default=False)),
                ("notified", models.BooleanField(default=False)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="instructions",
                        to="organizations.organization",
                    ),
                ),
                (
                    "owner",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="owned_instructions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "people_groups",
                    models.ManyToManyField(
                        blank=True,
                        related_name="instructions",
                        to="accounts.peoplegroup",
                    ),
                ),
            ],
            bases=(
                models.Model,
                apps.commons.mixins.OrganizationRelated,
                apps.commons.mixins.HasOwner,
            ),
        ),
    ]
