# Generated by Django 4.2.15 on 2024-10-01 13:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("skills", "0001_initial"),
        ("organizations", "0012_alter_organization_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="tags",
            field=models.ManyToManyField(
                blank=True,
                db_table="organizations_organization_skills_tags",
                related_name="organizations",
                to="skills.tag",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="enabled_tag_classifications",
            field=models.ManyToManyField(
                blank=True,
                related_name="enabled_organizations",
                to="skills.tagclassification",
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="default_tag_classification",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="default_organizations",
                to="skills.tagclassification",
            ),
        ),
        migrations.AddField(
            model_name="projectcategory",
            name="tags",
            field=models.ManyToManyField(
                blank=True,
                db_table="organizations_projectcategory_skills_tags",
                related_name="project_categories",
                to="skills.tag",
            ),
        ),
        migrations.AlterModelOptions(
            name="organization",
            options={
                "permissions": (
                    ("view_stat", "Can view stats"),
                    ("view_org_project", "Can view community projects"),
                    ("view_org_projectuser", "Can view community users"),
                    ("view_org_peoplegroup", "Can view community groups"),
                    ("lock_project", "Can lock and unlock a project"),
                    ("duplicate_project", "Can duplicate a project"),
                    ("change_locked_project", "Can update a locked project"),
                    ("manage_accessrequest", "Can manage access requests"),
                    ("view_project", "Can view projects"),
                    ("add_project", "Can add projects"),
                    ("change_project", "Can change projects"),
                    ("delete_project", "Can delete projects"),
                    ("view_projectmessage", "Can view project messages"),
                    ("add_projectmessage", "Can add project messages"),
                    ("change_projectmessage", "Can change project messages"),
                    ("delete_projectmessage", "Can delete project messages"),
                    ("view_projectuser", "Can view users"),
                    ("add_projectuser", "Can add users"),
                    ("change_projectuser", "Can change users"),
                    ("delete_projectuser", "Can delete users"),
                    ("view_peoplegroup", "Can view groups"),
                    ("add_peoplegroup", "Can add groups"),
                    ("change_peoplegroup", "Can change groups"),
                    ("delete_peoplegroup", "Can delete groups"),
                    ("add_tag", "Can add tags"),
                    ("change_tag", "Can change tags"),
                    ("delete_tag", "Can delete tags"),
                    ("add_tagclassification", "Can add tag classifications"),
                    ("change_tagclassification", "Can change tag classifications"),
                    ("delete_tagclassification", "Can delete tag classifications"),
                    ("add_faq", "Can add faqs"),
                    ("change_faq", "Can change faqs"),
                    ("delete_faq", "Can delete faqs"),
                    ("add_projectcategory", "Can add project categories"),
                    ("change_projectcategory", "Can change project categories"),
                    ("delete_projectcategory", "Can delete project categories"),
                    ("add_review", "Can add reviews"),
                    ("change_review", "Can change reviews"),
                    ("delete_review", "Can delete reviews"),
                    ("add_comment", "Can add comments"),
                    ("change_comment", "Can change comments"),
                    ("delete_comment", "Can delete comments"),
                    ("add_follow", "Can add follows"),
                    ("change_follow", "Can change follows"),
                    ("delete_follow", "Can delete follows"),
                    ("add_invitation", "Can add invitation links"),
                    ("change_invitation", "Can change invitation links"),
                    ("delete_invitation", "Can delete invitation links"),
                    ("add_news", "Can add news"),
                    ("change_news", "Can change news"),
                    ("delete_news", "Can delete news"),
                    ("add_event", "Can add event"),
                    ("change_event", "Can change event"),
                    ("delete_event", "Can delete event"),
                    ("add_instruction", "Can add instructions"),
                    ("change_instruction", "Can change instructions"),
                    ("delete_instruction", "Can delete instructions"),
                )
            },
        ),
    ]