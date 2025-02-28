# Generated by Django 4.2.15 on 2024-10-03 18:29

import apps.commons.mixins
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("goals", "0003_alter_goal_project"),
        ("projects", "0007_alter_projectmessage_project"),
    ]

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
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="goals",
                        to="projects.project",
                    ),
                ),
            ],
            bases=(
                models.Model,
                apps.commons.mixins.ProjectRelated,
                apps.commons.mixins.OrganizationRelated,
            ),
        ),
    ]
