# Generated by Django 4.2.16 on 2024-11-29 15:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0008_goal"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicalproject",
            name="duplicated_from",
            field=models.CharField(blank=True, default=None, max_length=8, null=True),
        ),
        migrations.AddField(
            model_name="project",
            name="duplicated_from",
            field=models.CharField(blank=True, default=None, max_length=8, null=True),
        ),
    ]
