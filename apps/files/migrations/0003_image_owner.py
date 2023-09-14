# Generated by Django 3.2.12 on 2022-04-20 08:54

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('files', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='image',
            name='owner',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, to_field='keycloak_id'),
        ),
    ]
