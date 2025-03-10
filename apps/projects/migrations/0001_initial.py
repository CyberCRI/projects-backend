# Generated by Django 4.2.7 on 2024-01-05 17:16

import apps.commons.mixins
import apps.projects.models
from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("organizations", "0001_initial"),
        ("files", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("misc", "0002_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="HistoricalProject",
            fields=[
                (
                    "id",
                    models.CharField(
                        auto_created=True,
                        db_index=True,
                        default=apps.projects.models.uuid_generator,
                        max_length=8,
                    ),
                ),
                ("permissions_up_to_date", models.BooleanField(default=False)),
                ("title", models.CharField(max_length=255, verbose_name="title")),
                ("slug", models.SlugField()),
                ("description", models.TextField(blank=True, default="")),
                ("purpose", models.TextField(blank=True, verbose_name="main goal")),
                ("is_locked", models.BooleanField(default=False)),
                ("is_shareable", models.BooleanField(default=False)),
                (
                    "publication_status",
                    models.CharField(
                        choices=[
                            ("public", "Public"),
                            ("private", "Private"),
                            ("org", "Org"),
                        ],
                        default="private",
                        max_length=10,
                        verbose_name="visibility",
                    ),
                ),
                (
                    "life_status",
                    models.CharField(
                        choices=[
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("canceled", "Canceled"),
                            ("toreview", "To Review"),
                        ],
                        default="running",
                        max_length=10,
                        verbose_name="life status",
                    ),
                ),
                (
                    "language",
                    models.CharField(
                        choices=[("fr", "French"), ("en", "English")],
                        default="en",
                        max_length=2,
                    ),
                ),
                ("created_at", models.DateTimeField(blank=True, editable=False)),
                ("updated_at", models.DateTimeField(blank=True, editable=False)),
                ("deleted_at", models.DateTimeField(null=True)),
                (
                    "sdgs",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.PositiveSmallIntegerField(
                            choices=[
                                (1, "No poverty"),
                                (2, "Zero hunger"),
                                (3, "Good health and well-being"),
                                (4, "Quality education"),
                                (5, "Gender equality"),
                                (6, "Clean water and sanitation"),
                                (7, "Affordable and clean energy"),
                                (8, "Decent work and economic growth"),
                                (9, "Industry, innovation and infrastructure"),
                                (10, "Reduces inequalities"),
                                (11, "Sustainable cities and communities"),
                                (12, "Responsible consumption & production"),
                                (13, "Climate action"),
                                (14, "Life below water"),
                                (15, "Life on land"),
                                (16, "Peace, justice and strong institutions"),
                                (17, "Partnerships for the goals"),
                            ]
                        ),
                        blank=True,
                        default=list,
                        size=17,
                        verbose_name="sustainable development goals",
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
                (
                    "header_image",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="files.image",
                    ),
                ),
            ],
            options={
                "verbose_name": "historical project",
                "verbose_name_plural": "historical projects",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="Project",
            fields=[
                (
                    "id",
                    models.CharField(
                        auto_created=True,
                        default=apps.projects.models.uuid_generator,
                        max_length=8,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("permissions_up_to_date", models.BooleanField(default=False)),
                ("title", models.CharField(max_length=255, verbose_name="title")),
                ("slug", models.SlugField(unique=True)),
                ("description", models.TextField(blank=True, default="")),
                ("purpose", models.TextField(blank=True, verbose_name="main goal")),
                ("is_locked", models.BooleanField(default=False)),
                ("is_shareable", models.BooleanField(default=False)),
                (
                    "publication_status",
                    models.CharField(
                        choices=[
                            ("public", "Public"),
                            ("private", "Private"),
                            ("org", "Org"),
                        ],
                        default="private",
                        max_length=10,
                        verbose_name="visibility",
                    ),
                ),
                (
                    "life_status",
                    models.CharField(
                        choices=[
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("canceled", "Canceled"),
                            ("toreview", "To Review"),
                        ],
                        default="running",
                        max_length=10,
                        verbose_name="life status",
                    ),
                ),
                (
                    "language",
                    models.CharField(
                        choices=[("fr", "French"), ("en", "English")],
                        default="en",
                        max_length=2,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("deleted_at", models.DateTimeField(null=True)),
                (
                    "sdgs",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.PositiveSmallIntegerField(
                            choices=[
                                (1, "No poverty"),
                                (2, "Zero hunger"),
                                (3, "Good health and well-being"),
                                (4, "Quality education"),
                                (5, "Gender equality"),
                                (6, "Clean water and sanitation"),
                                (7, "Affordable and clean energy"),
                                (8, "Decent work and economic growth"),
                                (9, "Industry, innovation and infrastructure"),
                                (10, "Reduces inequalities"),
                                (11, "Sustainable cities and communities"),
                                (12, "Responsible consumption & production"),
                                (13, "Climate action"),
                                (14, "Life below water"),
                                (15, "Life on land"),
                                (16, "Peace, justice and strong institutions"),
                                (17, "Partnerships for the goals"),
                            ]
                        ),
                        blank=True,
                        default=list,
                        size=17,
                        verbose_name="sustainable development goals",
                    ),
                ),
                (
                    "categories",
                    models.ManyToManyField(
                        related_name="projects",
                        to="organizations.projectcategory",
                        verbose_name="categories",
                    ),
                ),
                (
                    "groups",
                    models.ManyToManyField(related_name="projects", to="auth.group"),
                ),
                (
                    "header_image",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="project_header",
                        to="files.image",
                    ),
                ),
                (
                    "images",
                    models.ManyToManyField(related_name="projects", to="files.image"),
                ),
                (
                    "main_category",
                    simple_history.models.HistoricForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="organizations.projectcategory",
                        verbose_name="main category",
                    ),
                ),
                (
                    "organization_tags",
                    models.ManyToManyField(
                        to="misc.tag", verbose_name="organizational tags"
                    ),
                ),
                (
                    "organizations",
                    models.ManyToManyField(
                        related_name="projects", to="organizations.organization"
                    ),
                ),
                (
                    "wikipedia_tags",
                    models.ManyToManyField(
                        related_name="projects",
                        to="misc.wikipediatag",
                        verbose_name="wikipedia tags",
                    ),
                ),
            ],
            options={
                "permissions": (
                    ("lock_project", "Can lock and unlock a project"),
                    ("duplicate_project", "Can duplicate a project"),
                    ("change_locked_project", "Can update a locked project"),
                    ("add_review", "Can add project's reviews"),
                    ("change_review", "Can change project's reviews"),
                    ("delete_review", "Can delete project's reviews"),
                    ("add_comment", "Can add project's comments"),
                    ("change_comment", "Can change project's comments"),
                    ("delete_comment", "Can delete project's comments"),
                    ("add_follow", "Can add project's follows"),
                    ("change_follow", "Can change project's follows"),
                    ("delete_follow", "Can delete project's follows"),
                ),
                "write_only_subscopes": (
                    ("review", "project's reviews"),
                    ("comment", "project's comments"),
                    ("follow", "project's follows"),
                ),
            },
            bases=(
                apps.commons.mixins.HasMultipleIDs,
                models.Model,
                apps.commons.mixins.ProjectRelated,
                apps.commons.mixins.OrganizationRelated,
            ),
        ),
        migrations.CreateModel(
            name="Location",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(blank=True, max_length=255)),
                ("description", models.TextField(blank=True)),
                ("lat", models.FloatField()),
                ("lng", models.FloatField()),
                (
                    "type",
                    models.CharField(
                        choices=[("team", "Team"), ("impact", "Impact")],
                        default="team",
                        max_length=6,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="locations",
                        to="projects.project",
                    ),
                ),
            ],
            bases=(
                models.Model,
                apps.commons.mixins.ProjectRelated,
                apps.commons.mixins.OrganizationRelated,
            ),
        ),
        migrations.CreateModel(
            name="HistoricalProject_wikipedia_tags",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                ("m2m_history_id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "history",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="projects.historicalproject",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        db_tablespace="",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="projects.project",
                    ),
                ),
                (
                    "wikipediatag",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        db_tablespace="",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="misc.wikipediatag",
                    ),
                ),
            ],
            options={
                "verbose_name": "HistoricalProject_wikipedia_tags",
            },
        ),
        migrations.CreateModel(
            name="HistoricalProject_organization_tags",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                ("m2m_history_id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "history",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="projects.historicalproject",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        db_tablespace="",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="projects.project",
                    ),
                ),
                (
                    "tag",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        db_tablespace="",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="misc.tag",
                    ),
                ),
            ],
            options={
                "verbose_name": "HistoricalProject_organization_tags",
            },
        ),
        migrations.CreateModel(
            name="HistoricalProject_categories",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                ("m2m_history_id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "history",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="projects.historicalproject",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        db_tablespace="",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="projects.project",
                    ),
                ),
                (
                    "projectcategory",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        db_tablespace="",
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="organizations.projectcategory",
                    ),
                ),
            ],
            options={
                "verbose_name": "HistoricalProject_categories",
            },
        ),
        migrations.AddField(
            model_name="historicalproject",
            name="history_relation",
            field=models.ForeignKey(
                db_constraint=False,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="archive",
                to="projects.project",
            ),
        ),
        migrations.AddField(
            model_name="historicalproject",
            name="history_user",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="+",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="historicalproject",
            name="main_category",
            field=simple_history.models.HistoricForeignKey(
                blank=True,
                db_constraint=False,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="+",
                to="organizations.projectcategory",
                verbose_name="main category",
            ),
        ),
        migrations.CreateModel(
            name="HistoricalLinkedProject",
            fields=[
                (
                    "id",
                    models.BigIntegerField(
                        auto_created=True, blank=True, db_index=True, verbose_name="ID"
                    ),
                ),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                (
                    "history_type",
                    models.CharField(
                        choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")],
                        max_length=1,
                    ),
                ),
                (
                    "history_user",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="projects.project",
                    ),
                ),
                (
                    "target",
                    simple_history.models.HistoricForeignKey(
                        blank=True,
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        related_name="+",
                        to="projects.project",
                    ),
                ),
            ],
            options={
                "verbose_name": "historical linked project",
                "verbose_name_plural": "historical linked projects",
                "ordering": ("-history_date", "-history_id"),
                "get_latest_by": ("history_date", "history_id"),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name="BlogEntry",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(max_length=255)),
                ("content", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "images",
                    models.ManyToManyField(
                        related_name="blog_entries", to="files.image"
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="blog_entries",
                        to="projects.project",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
            bases=(
                models.Model,
                apps.commons.mixins.ProjectRelated,
                apps.commons.mixins.OrganizationRelated,
            ),
        ),
        migrations.CreateModel(
            name="LinkedProject",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="linked_to",
                        to="projects.project",
                    ),
                ),
                (
                    "target",
                    simple_history.models.HistoricForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="linked_projects",
                        to="projects.project",
                    ),
                ),
            ],
            options={
                "unique_together": {("project", "target")},
            },
            bases=(
                models.Model,
                apps.commons.mixins.ProjectRelated,
                apps.commons.mixins.OrganizationRelated,
            ),
        ),
    ]
