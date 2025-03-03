# Generated by Django 4.2.7 on 2024-01-05 17:16

import apps.commons.mixins
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

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
                ("name", models.CharField(max_length=255)),
            ],
            bases=(models.Model, apps.commons.mixins.OrganizationRelated),
        ),
        migrations.CreateModel(
            name="WikipediaTag",
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
                ("name", models.CharField(help_text="name of the tag", max_length=255)),
                (
                    "name_en",
                    models.CharField(
                        help_text="name of the tag", max_length=255, null=True
                    ),
                ),
                (
                    "name_fr",
                    models.CharField(
                        help_text="name of the tag", max_length=255, null=True
                    ),
                ),
                (
                    "wikipedia_qid",
                    models.CharField(
                        help_text="Wikidata item ID, e.g https://www.wikidata.org/wiki/Q1 is Q1",
                        max_length=50,
                        unique=True,
                    ),
                ),
            ],
        ),
    ]
