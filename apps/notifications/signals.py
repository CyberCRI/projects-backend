from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import ProjectUser
from apps.newsfeed.models import Instruction
from apps.notifications.utils import send_instruction_notification_if_needed

from .models import Notification, NotificationSettings
from django.utils import timezone
from apps.newsfeed.models import Instruction
from apps.emailing.utils import render_message, send_email


@receiver(post_save, sender=ProjectUser)
def create_notification_settings(sender, instance, created, **kwargs):
    """Create the associated notification settings at user's creation."""
    if created:
        NotificationSettings.objects.create(user=instance)

@receiver(post_save, sender=Instruction)
def create_instruction_notification(sender, instance, created, **kwargs):
    """Create the associated notification upon instruction creation."""
    send_instruction_notification_if_needed(instance)
    start_of_day = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    publication_day = instance.publication_date.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    
    if instance.has_to_be_notified and not instance.notified and start_of_day == publication_day:
        groups = instance.people_groups
        members = [group.members.all() for group in groups]
        receivers = set(members)
        for receiver in receivers:
            Notification.objects.create(
                receiver=receiver,
                type="instruction",
                instruction=instance,
            )

        subject, _ = render_message("notifications/instruction/object", receiver.language)
        text, html = render_message("notifications/instruction/mail", receiver.language)
        send_email(subject, text, [receiver.email], html_content=html)
        
        instance.notified = True
        instance.save()