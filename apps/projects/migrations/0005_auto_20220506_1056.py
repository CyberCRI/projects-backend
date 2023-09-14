# Generated by Django 3.2.13 on 2022-05-06 10:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('misc', '0002_rename_tag_wikipediatag'),
        ('projects', '0004_rename_tag_historicalproject_tags_wikipediatag'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='HistoricalProject_tags',
            new_name='HistoricalProject_wikipedia_tags',
        ),
        migrations.AlterModelOptions(
            name='historicalproject_wikipedia_tags',
            options={'verbose_name': 'HistoricalProject_wikipedia_tags'},
        ),
        migrations.RenameField(
            model_name='project',
            old_name='tags',
            new_name='wikipedia_tags',
        ),
    ]
