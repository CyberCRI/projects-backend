# Generated by Django 3.2.13 on 2022-05-15 20:31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('projects', '0011_alter_historicalproject_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectmember',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='projectmembers', to=settings.AUTH_USER_MODEL, to_field='keycloak_id'),
        ),
    ]
