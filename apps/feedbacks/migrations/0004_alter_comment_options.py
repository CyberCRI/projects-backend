# Generated by Django 3.2.13 on 2022-05-25 09:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feedbacks', '0003_alter_follow_follower'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='comment',
            options={'ordering': ['-created_at']},
        ),
    ]
