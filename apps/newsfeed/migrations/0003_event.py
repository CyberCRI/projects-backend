# Generated by Django 4.2.11 on 2024-04-11 12:52

import apps.commons.models
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_remove_peoplegroup_type"),
        ("organizations", "0004_alter_organization_options"),
        ("newsfeed", "0002_news"),
    ]

    operations = [
        migrations.CreateModel(
            name="Event",
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
                ("event_date", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="events",
                        to="organizations.organization",
                    ),
                ),
                (
                    "people_groups",
                    models.ManyToManyField(
                        related_name="events", to="accounts.peoplegroup"
                    ),
                ),
            ],
            bases=(models.Model, apps.commons.models.OrganizationRelated),
        ),
    ]