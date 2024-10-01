# Generated by Django 4.2.15 on 2024-10-01 13:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0004_alter_project_options"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="historicalproject_organization_tags",
            name="history",
        ),
        migrations.RemoveField(
            model_name="historicalproject_organization_tags",
            name="project",
        ),
        migrations.RemoveField(
            model_name="historicalproject_organization_tags",
            name="tag",
        ),
        migrations.RemoveField(
            model_name="historicalproject_wikipedia_tags",
            name="history",
        ),
        migrations.RemoveField(
            model_name="historicalproject_wikipedia_tags",
            name="project",
        ),
        migrations.RemoveField(
            model_name="historicalproject_wikipedia_tags",
            name="wikipediatag",
        ),
        migrations.DeleteModel(
            name="HistoricalProject_organization_tags",
        ),
        migrations.DeleteModel(
            name="HistoricalProject_wikipedia_tags",
        ),
    ]
