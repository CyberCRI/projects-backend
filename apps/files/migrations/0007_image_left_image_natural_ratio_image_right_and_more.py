# Generated by Django 4.0.10 on 2023-03-15 11:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0006_auto_20220523_1643'),
    ]

    operations = [
        migrations.AddField(
            model_name='image',
            name='left',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='image',
            name='natural_ratio',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='image',
            name='right',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='image',
            name='scale_x',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='image',
            name='scale_y',
            field=models.FloatField(null=True),
        ),
    ]
