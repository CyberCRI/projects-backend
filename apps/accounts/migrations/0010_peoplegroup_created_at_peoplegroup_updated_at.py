# Generated by Django 4.2.16 on 2024-11-27 10:03

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0009_alter_skill_user"),
    ]

    operations = [
        migrations.AddField(
            model_name="peoplegroup",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="peoplegroup",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]
