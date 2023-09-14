# Generated by Django 3.2.13 on 2022-05-09 16:25

import apps.files.models
from django.db import migrations
import stdimage.models


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0003_image_owner'),
    ]

    operations = [
        migrations.AlterField(
            model_name='image',
            name='file',
            field=stdimage.models.StdImageField(height_field='height', upload_to=apps.files.models.dynamic_upload_to, width_field='width'),
        ),
    ]
