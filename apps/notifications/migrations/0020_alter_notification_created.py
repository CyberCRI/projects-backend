# Generated by Django 4.0.10 on 2023-03-24 15:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0019_notification_count'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notification',
            name='created',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
