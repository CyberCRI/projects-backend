# Generated by Django 4.2.11 on 2024-06-14 10:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_userscore"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="projectuser",
            options={
                "permissions": (("get_user_by_email", "Can retrieve a user by email"),)
            },
        ),
    ]