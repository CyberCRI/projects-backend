# Generated by Django 4.2.11 on 2024-03-28 17:06

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0003_organization_identity_providers"),
        ("notifications", "0003_notification_access_request_alter_notification_type"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="notification",
            name="invitation",
        ),
        migrations.AddField(
            model_name="notification",
            name="organization",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="organizations.organization",
            ),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="invitation_link_will_expire",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="notificationsettings",
            name="organization_has_new_access_request",
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name="notification",
            name="type",
            field=models.CharField(
                choices=[
                    ("comment", "Comment"),
                    ("reply", "Reply"),
                    ("review", "Review"),
                    ("ready_for_review", "Ready For Review"),
                    ("project_updated", "Project Updated"),
                    ("member_added_self", "Member Added Self"),
                    ("group_member_added_self", "Group Member Added Self"),
                    ("member_updated_self", "Member Updated Self"),
                    ("member_added", "Member Added"),
                    ("member_updated", "Member Updated"),
                    ("member_removed", "Member Removed"),
                    ("group_member_removed", "Group Member Removed"),
                    ("group_member_added", "Group Member Added"),
                    ("announcement", "Announcement"),
                    ("application", "Application"),
                    ("blog_entry", "Blog Entry"),
                    ("invitation_today_reminder", "Invitation Today Reminder"),
                    ("invitation_week_reminder", "Invitation Week Reminder"),
                    ("access_request", "Access Request"),
                    ("pending_access_requests", "Pending Access Requests"),
                ],
                default="project_updated",
                max_length=30,
            ),
        ),
    ]
