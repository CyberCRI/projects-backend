# Generated by Django 4.0.5 on 2022-06-29 08:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organizations', '0014_merge_20220607_1514'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='organization',
            name='is_logo_visible_on_parent_dashboard',
        ),
    ]
