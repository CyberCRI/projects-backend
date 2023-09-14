# Generated by Django 4.0.7 on 2022-10-17 15:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0010_remove_projectuser_skills_remove_skill_title_and_more'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='skill',
            constraint=models.UniqueConstraint(fields=('user', 'wikipedia_tag'), name='unique user wikipedia_tag'),
        ),
    ]
