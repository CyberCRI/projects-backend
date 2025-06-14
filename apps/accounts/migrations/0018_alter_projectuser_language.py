# Generated by Django 4.2.20 on 2025-06-12 08:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0017_alter_peoplegroup_organization"),
    ]

    operations = [
        migrations.AlterField(
            model_name="projectuser",
            name="language",
            field=models.CharField(
                choices=[
                    ("en", "English"),
                    ("fr", "Français"),
                    ("de", "Deutsch"),
                    ("nl", "Dutch"),
                    ("et", "Estonian"),
                    ("ca", "Catalan"),
                ],
                default="en",
                max_length=2,
            ),
        ),
    ]
