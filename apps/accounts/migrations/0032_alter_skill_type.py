# Generated by Django 4.2.1 on 2023-06-06 14:04

from django.db import migrations, models


def update_skills(apps, schema_editor):
    skills = apps.get_model("accounts", "Skill")
    db_alias = schema_editor.connection.alias
    skills.objects.using(db_alias).filter(type="personal").update(type="skill")
    skills.objects.using(db_alias).filter(type="academic").update(type="skill")

def update_privacy_settings(apps, schema_editor):

    privacy_settings = apps.get_model("accounts", "PrivacySettings")
    db_alias = schema_editor.connection.alias
    privacy_settings.objects.using(db_alias).filter(academic_skills="hide").update(academic_skills="org")
    privacy_settings.objects.using(db_alias).filter(personal_skills="hide").update(personal_skills="org")

class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0031_skill_category"),
    ]

    operations = [
        migrations.AlterField(
            model_name="skill",
            name="type",
            field=models.CharField(
                choices=[("skill", "Skill"), ("hobby", "Hobby")],
                default="skill",
                max_length=8,
            ),
        ),
        migrations.RunPython(update_skills, migrations.RunPython.noop),
        migrations.RunPython(update_privacy_settings, migrations.RunPython.noop),
    ]


