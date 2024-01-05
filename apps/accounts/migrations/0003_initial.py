# Generated by Django 4.2.7 on 2024-01-05 17:16

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("projects", "0001_initial"),
        ("files", "0002_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("organizations", "0001_initial"),
        ("accounts", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="peoplegroup",
            name="featured_projects",
            field=models.ManyToManyField(
                related_name="people_groups", to="projects.project"
            ),
        ),
        migrations.AddField(
            model_name="peoplegroup",
            name="groups",
            field=models.ManyToManyField(related_name="people_groups", to="auth.group"),
        ),
        migrations.AddField(
            model_name="peoplegroup",
            name="header_image",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="people_group_header",
                to="files.image",
            ),
        ),
        migrations.AddField(
            model_name="peoplegroup",
            name="logo_image",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="people_group_logo",
                to="files.image",
            ),
        ),
        migrations.AddField(
            model_name="peoplegroup",
            name="organization",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="organizations.organization",
            ),
        ),
        migrations.AddField(
            model_name="peoplegroup",
            name="parent",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="children",
                to="accounts.peoplegroup",
            ),
        ),
        migrations.AddField(
            model_name="projectuser",
            name="groups",
            field=models.ManyToManyField(related_name="users", to="auth.group"),
        ),
        migrations.AddField(
            model_name="projectuser",
            name="profile_picture",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="user",
                to="files.image",
            ),
        ),
        migrations.AddField(
            model_name="projectuser",
            name="user_permissions",
            field=models.ManyToManyField(
                blank=True,
                help_text="Specific permissions for this user.",
                related_name="user_set",
                related_query_name="user",
                to="auth.permission",
                verbose_name="user permissions",
            ),
        ),
        migrations.AddConstraint(
            model_name="skill",
            constraint=models.UniqueConstraint(
                fields=("user", "wikipedia_tag"), name="unique user wikipedia_tag"
            ),
        ),
        migrations.AddConstraint(
            model_name="peoplegroup",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_root", True)),
                fields=("organization",),
                name="unique_root_group_per_organization",
            ),
        ),
    ]
