# Generated by Django 4.2.1 on 2023-06-14 14:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("deploys", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="postdeployprocess",
            name="error",
            field=models.TextField(blank=True, default=""),
        ),
    ]
