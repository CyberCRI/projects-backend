from django.db import models


class MentorshipContact(models.Model):
    """
    MentorshipContact instance to store contacts made between mentors and mentorees.

    Attributes
    ----------
    sender: ForeignKey
        The sender of the mentorship contact.
    receiver: ForeignKey
        The receiver of the mentorship contact.
    old_skill: ForeignKey
        The skill in the mentorship contact.
    contact_type: CharField
        If the contact was made by the mentor or the mentoree.
    """

    class ContactTypeChoices(models.TextChoices):
        """Choices for the contact_from field."""

        MENTOR_REQUEST = "mentor_request"
        MENTOREE_REQUEST = "mentoree_request"

    sender = models.ForeignKey(
        "accounts.ProjectUser",
        related_name="sent_mentorship_contacts",
        on_delete=models.CASCADE,
    )
    mentor = models.ForeignKey(
        "accounts.ProjectUser",
        related_name="received_mentorship_contacts",
        on_delete=models.CASCADE,
    )
    old_skill = models.ForeignKey(
        "accounts.Skill",
        related_name="mentorship_contacts",
        on_delete=models.CASCADE,
    )
    contact_type = models.CharField(
        max_length=255,
        choices=ContactTypeChoices.choices,
        default=ContactTypeChoices.MENTOR_REQUEST,
    )
    created_at = models.DateTimeField(auto_now_add=True)
