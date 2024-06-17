# Generated by Django 4.2.11 on 2024-05-29 15:45

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_remove_peoplegroup_type"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserScore",
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
                ("completeness", models.FloatField(default=0)),
                ("activity", models.FloatField(default=0)),
                ("score", models.FloatField(default=0)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="score",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]