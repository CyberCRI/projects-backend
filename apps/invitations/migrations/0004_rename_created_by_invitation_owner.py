# Generated by Django 4.0.10 on 2023-05-17 09:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('invitations', '0003_alter_invitation_people_group'),
    ]

    operations = [
        migrations.RenameField(
            model_name='invitation',
            old_name='created_by',
            new_name='owner',
        ),
    ]
