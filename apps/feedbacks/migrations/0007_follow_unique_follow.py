# Generated by Django 4.2.3 on 2023-11-02 15:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("feedbacks", "0006_comment_images"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="follow",
            constraint=models.UniqueConstraint(
                fields=("project", "follower"), name="unique_follow"
            ),
        ),
    ]
