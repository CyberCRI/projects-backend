# Generated by Django 4.2.7 on 2023-12-18 14:58

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0032_alter_organization_options_and_more"),
        ("accounts", "0059_merge_20231212_1834"),
    ]

    operations = [
        migrations.CreateModel(
            name="AccessRequest",
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
                ("email", models.CharField(blank=True, max_length=255)),
                ("given_name", models.CharField(blank=True, max_length=255)),
                ("family_name", models.CharField(blank=True, max_length=255)),
                ("job", models.CharField(blank=True, max_length=255)),
                ("message", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("accepted", "Accepted"),
                            ("declined", "Declined"),
                        ],
                        default="pending",
                        max_length=10,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_requests",
                        to="organizations.organization",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "permissions": (
                    ("manage_accessrequest", "Can manage access requests"),
                ),
            },
        ),
    ]
