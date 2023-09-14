# Generated by Django 4.2.3 on 2023-08-07 14:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0038_rename_facebook_privacysettings_socials_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="privacysettings",
            name="mobile_phone",
            field=models.CharField(
                choices=[("hide", "Hide"), ("org", "Organization"), ("pub", "Public")],
                default="org",
                max_length=4,
            ),
        ),
        migrations.AlterField(
            model_name="privacysettings",
            name="personal_email",
            field=models.CharField(
                choices=[("hide", "Hide"), ("org", "Organization"), ("pub", "Public")],
                default="org",
                max_length=4,
            ),
        ),
        migrations.AlterField(
            model_name="privacysettings",
            name="skills",
            field=models.CharField(
                choices=[("hide", "Hide"), ("org", "Organization"), ("pub", "Public")],
                default="pub",
                max_length=4,
            ),
        ),
    ]
