# Generated by Django 4.2.3 on 2023-07-31 14:17

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0040_peoplegroup_old_groups"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="projectuser",
            name="permissions",
        ),
        migrations.DeleteModel(
            name="ServiceAccount",
        ),
    ]
