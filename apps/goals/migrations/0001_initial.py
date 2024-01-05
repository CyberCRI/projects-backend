# Generated by Django 4.2.7 on 2024-01-05 17:16

import apps.commons.db.abc
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Goal",
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
                ("title", models.CharField(blank=True, max_length=255)),
                ("description", models.TextField(blank=True)),
                ("deadline_at", models.DateField(null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("na", "None"),
                            ("ongoing", "Ongoing"),
                            ("complete", "Complete"),
                            ("cancel", "Cancel"),
                        ],
                        default="na",
                        max_length=24,
                    ),
                ),
            ],
            bases=(
                models.Model,
                apps.commons.db.abc.ProjectRelated,
                apps.commons.db.abc.OrganizationRelated,
            ),
        ),
    ]
