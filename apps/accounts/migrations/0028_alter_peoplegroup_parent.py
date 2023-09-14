# Generated by Django 4.0.10 on 2023-04-17 13:49

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0027_peoplegroup_sdgs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='peoplegroup',
            name='parent',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='children', to='accounts.peoplegroup'),
        ),
    ]
