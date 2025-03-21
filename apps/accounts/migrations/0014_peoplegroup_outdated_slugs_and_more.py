# Generated by Django 4.2.18 on 2025-02-11 14:48

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0013_remove_peoplegroup_order_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="peoplegroup",
            name="outdated_slugs",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.SlugField(), default=list, size=None
            ),
        ),
        migrations.AddField(
            model_name="projectuser",
            name="outdated_slugs",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.SlugField(), default=list, size=None
            ),
        ),
    ]
