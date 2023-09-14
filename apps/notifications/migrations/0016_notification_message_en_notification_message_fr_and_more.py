# Generated by Django 4.0.7 on 2022-12-13 15:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0015_notification_reminder_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='message_en',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='notification',
            name='message_fr',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='notification',
            name='reminder_message_en',
            field=models.CharField(blank=True, default='', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='notification',
            name='reminder_message_fr',
            field=models.CharField(blank=True, default='', max_length=255, null=True),
        ),
    ]
