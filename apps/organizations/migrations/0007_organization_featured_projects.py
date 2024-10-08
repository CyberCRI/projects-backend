# Generated by Django 4.2.10 on 2024-04-16 09:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0001_initial"),
        ("organizations", "0006_alter_organization_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="featured_projects",
            field=models.ManyToManyField(
                related_name="org_featured_projects", to="projects.project"
            ),
        ),
    ]
