# Generated by Django 4.2.18 on 2025-02-03 14:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0018_remove_organization_wikipedia_tags_and_more"),
        ("skills", "0006_tag_alternative_titles_tag_alternative_titles_en_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="mentoring",
            name="organization",
            field=models.ForeignKey(
                default=1,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="mentorings",
                to="organizations.organization",
            ),
            preserve_default=False,
        ),
    ]
