from typing import Type

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.announcements.models import Announcement
from apps.feedbacks.models import Comment
from apps.files.models import AttachmentFile, AttachmentLink
from apps.projects.models import BlogEntry, Goal, LinkedProject, Location


@receiver(post_save, sender="projects.BlogEntry")
def on_blog_entry_change(
    sender: Type[BlogEntry], instance: BlogEntry, created: bool, **kwargs
):
    project = instance.project
    action = "Added" if created else "Updated"
    project._change_reason = action + " blog entry"
    project.save()


@receiver(post_delete, sender="projects.BlogEntry")
def on_blog_entry_delete(sender: Type[BlogEntry], instance: BlogEntry, **kwargs):
    project = instance.project
    project._change_reason = "Removed blog entry"
    project.save()


@receiver(post_save, sender="projects.Goal")
def on_goal_change(sender: Type[Goal], instance: Goal, created: bool, **kwargs):
    project = instance.project
    action = "Added" if created else "Updated"
    project._change_reason = action + " goal"
    project.save()


@receiver(post_delete, sender="projects.Goal")
def on_goal_delete(sender: Type[Goal], instance: Goal, **kwargs):
    project = instance.project
    project._change_reason = "Removed goal"
    project.save()


@receiver(post_save, sender="projects.Location")
def on_location_change(
    sender: Type[Location], instance: Location, created: bool, **kwargs
):
    project = instance.project
    action = "Added" if created else "Updated"
    project._change_reason = action + " location"
    project.save()


@receiver(post_delete, sender="projects.Location")
def on_location_delete(sender: Type[Location], instance: Location, **kwargs):
    project = instance.project
    project._change_reason = "Removed location"
    project.save()


@receiver(post_save, sender="projects.LinkedProject")
def on_linked_project_change(
    sender: Type[LinkedProject], instance: LinkedProject, created: bool, **kwargs
):
    project = instance.target
    action = "Added" if created else "Updated"
    project._change_reason = action + " linked project"
    project.save()


@receiver(post_delete, sender="projects.LinkedProject")
def on_linked_project_delete_post(
    sender: Type[LinkedProject], instance: LinkedProject, **kwargs
):
    project = instance.target
    project._change_reason = "Removed linked project"
    project.save()


@receiver(post_save, sender="feedbacks.Comment")
def on_comment_change(
    sender: Type[Comment], instance: Comment, created: bool, **kwargs
):
    project = instance.project
    action = "Added" if created else ("Removed" if instance.deleted_at else "Updated")
    project._change_reason = action + " comment"
    project.save()


@receiver(post_save, sender="files.AttachmentLink")
def on_attachment_link_change(
    sender: Type[AttachmentLink], instance: AttachmentLink, created: bool, **kwargs
):
    project = instance.project
    action = "Added" if created else "Updated"
    project._change_reason = action + " attachment link"
    project.save()


@receiver(post_delete, sender="files.AttachmentLink")
def on_attachment_link_delete(
    sender: Type[AttachmentLink], instance: AttachmentLink, **kwargs
):
    project = instance.project
    project._change_reason = "Removed attachment link"
    project.save()


@receiver(post_save, sender="files.AttachmentFile")
def on_attachment_file_change(
    sender: Type[AttachmentFile], instance: AttachmentFile, created: bool, **kwargs
):
    project = instance.project
    action = "Added" if created else "Updated"
    project._change_reason = action + " attachment file"
    project.save()


@receiver(post_delete, sender="files.AttachmentFile")
def on_attachment_file_delete(
    sender: Type[AttachmentFile], instance: AttachmentFile, **kwargs
):
    project = instance.project
    project._change_reason = "Removed attachment file"
    project.save()


@receiver(post_save, sender="announcements.Announcement")
def on_announcement_change(
    sender: Type[Announcement], instance: Announcement, created: bool, **kwargs
):
    project = instance.project
    action = "Added" if created else "Updated"
    project._change_reason = action + " announcement"
    project.save()


@receiver(post_delete, sender="announcements.Announcement")
def on_announcement_delete(
    sender: Type[Announcement], instance: Announcement, **kwargs
):
    project = instance.project
    project._change_reason = "Removed announcement"
    project.save()
