# Generated by Django 4.2.1 on 2023-06-05 12:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0030_peoplegroup_publication_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='peoplegroup',
            name='is_root',
            field=models.BooleanField(default=False),
        ),
        migrations.AddConstraint(
            model_name='peoplegroup',
            constraint=models.UniqueConstraint(
                condition=models.Q(('is_root', True)),
                fields=('organization',),
                name='unique_root_group_per_organization',
            ),
        ),
    ]
