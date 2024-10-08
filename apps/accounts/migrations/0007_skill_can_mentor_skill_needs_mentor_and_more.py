# Generated by Django 4.2.14 on 2024-07-26 12:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("misc", "0003_wikipediatag_description_wikipediatag_description_en_and_more"),
        ("accounts", "0006_alter_projectuser_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="skill",
            name="can_mentor",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="skill",
            name="needs_mentor",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="skill",
            name="wikipedia_tag",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="skills",
                to="misc.wikipediatag",
            ),
        ),
    ]
