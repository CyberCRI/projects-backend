from typing import Callable, List, Optional

from django.core.management.base import BaseCommand
from django.db.models import Model

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.announcements.models import Announcement
from apps.commons.utils import process_text
from apps.feedbacks.models import Comment, Review
from apps.files.models import AttachmentFile, AttachmentLink, OrganizationAttachmentFile
from apps.invitations.models import AccessRequest, Invitation
from apps.newsfeed.models import Event, Instruction, News
from apps.organizations.models import (
    Organization,
    ProjectCategory,
    Template,
    TermsAndConditions,
)
from apps.projects.models import (
    BlogEntry,
    Goal,
    Location,
    Project,
    ProjectMessage,
    ProjectTab,
    ProjectTabItem,
)
from apps.skills.models import MentoringMessage, TagClassification


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform a dry run without saving changes to the database.",
        )

    def _handle_model(
        self,
        model_class: Model,
        images_fields: Optional[List[str]] = None,
        forbid_images_fields: Optional[List[str]] = None,
        upload_to: str = "",
        view: str = "",
        process_template: bool = False,
        get_kwargs: Optional[Callable] = None,
        get_owner: Optional[Callable] = None,
        dry_run: bool = False,
    ):
        images_fields = images_fields or []
        forbid_images_fields = forbid_images_fields or []
        if images_fields and (not upload_to or not view):
            raise ValueError(
                "upload_to and view must be provided if images_fields is used."
            )
        for field in forbid_images_fields:
            for instance in model_class.objects.filter(
                **{f"{field}__icontains": "data:image"}
            ):
                content = getattr(instance, field)
                new_content, _ = process_text(content, forbid_images=True)
                if dry_run:
                    if new_content != content:
                        self.stdout.write(
                            f"[DRY RUN] Would update {model_class.__name__} (ID: {instance.id}) field '{field}'"
                        )
                else:
                    model_class.objects.filter(id=instance.id).update(
                        **{field: new_content}
                    )
        for field in images_fields:
            for instance in model_class.objects.filter(
                **{f"{field}__icontains": "data:image"}
            ):
                content = getattr(instance, field)
                owner = get_owner(instance) if get_owner else None
                kwargs = get_kwargs(instance) if get_kwargs else {}
                new_content, images = process_text(
                    text=content,
                    instance=instance,
                    upload_to=upload_to,
                    view=view,
                    owner=owner,
                    process_template=process_template,
                    **kwargs,
                )
                if dry_run:
                    if new_content != content:
                        self.stdout.write(
                            f"[DRY RUN] Would update {model_class.__name__} (ID: {instance.id}) field '{field}' and add {len(images)} images"
                        )
                else:
                    instance.images.add(*images)
                    model_class.objects.filter(id=instance.id).update(
                        **{field: new_content}
                    )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)
        self._handle_model(
            PeopleGroup,
            forbid_images_fields=["name", "description", "short_description"],
            dry_run=dry_run,
        )
        self._handle_model(
            ProjectUser,
            forbid_images_fields=["description", "short_description", "job"],
            dry_run=dry_run,
        )
        self._handle_model(
            Announcement, forbid_images_fields=["title", "description"], dry_run=dry_run
        )
        self._handle_model(
            Comment,
            images_fields=["content"],
            upload_to="comment/images/",
            view="Comment-images-detail",
            process_template=True,
            get_kwargs=lambda instance: {"project_id": instance.project.id},
            get_owner=lambda instance: instance.author,
            dry_run=dry_run,
        )
        self._handle_model(
            Review, forbid_images_fields=["title", "description"], dry_run=dry_run
        )
        self._handle_model(
            AttachmentLink,
            forbid_images_fields=["description", "title"],
            dry_run=dry_run,
        )
        self._handle_model(
            OrganizationAttachmentFile,
            forbid_images_fields=["description", "title"],
            dry_run=dry_run,
        )
        self._handle_model(
            AttachmentFile,
            forbid_images_fields=["description", "title"],
            dry_run=dry_run,
        )
        self._handle_model(
            Invitation, forbid_images_fields=["description"], dry_run=dry_run
        )
        self._handle_model(
            AccessRequest, forbid_images_fields=["message"], dry_run=dry_run
        )
        self._handle_model(
            News,
            images_fields=["content"],
            forbid_images_fields=["title"],
            upload_to="news/images/",
            view="News-images-detail",
            get_kwargs=lambda instance: {
                "organization_code": instance.organization.code,
                "news_id": instance.id,
            },
            dry_run=dry_run,
        )
        self._handle_model(
            Instruction,
            images_fields=["content"],
            forbid_images_fields=["title"],
            upload_to="instructions/images/",
            view="Instruction-images-detail",
            get_kwargs=lambda instance: {
                "organization_code": instance.organization.code,
                "instruction_id": instance.id,
            },
            get_owner=lambda instance: instance.owner,
            dry_run=dry_run,
        )
        self._handle_model(
            Event,
            images_fields=["content"],
            forbid_images_fields=["title"],
            upload_to="events/images/",
            view="Event-images-detail",
            get_kwargs=lambda instance: {
                "organization_code": instance.organization.code,
                "event_id": instance.id,
            },
            dry_run=dry_run,
        )
        self._handle_model(
            Organization,
            images_fields=["description"],
            forbid_images_fields=[
                "name",
                "dashboard_title",
                "dashboard_subtitle",
                "chat_button_text",
            ],
            upload_to="organization/images/",
            view="Organization-images-detail",
            get_kwargs=lambda instance: {"organization_code": instance.code},
            dry_run=dry_run,
        )
        self._handle_model(
            Template,
            images_fields=[
                "description",
                "project_description",
                "blogentry_content",
                "comment_content",
            ],
            forbid_images_fields=[
                "name",
                "project_title",
                "project_purpose",
                "goal_title",
                "goal_description",
                "review_title",
                "review_description",
            ],
            upload_to="template/images/",
            view="Template-images-detail",
            get_kwargs=lambda instance: {
                "organization_code": instance.organization.code,
                "template_id": instance.id,
            },
            dry_run=dry_run,
        )
        self._handle_model(
            ProjectCategory,
            forbid_images_fields=["name", "description"],
            dry_run=dry_run,
        )
        self._handle_model(
            TermsAndConditions, forbid_images_fields=["content"], dry_run=dry_run
        )
        self._handle_model(
            Project,
            images_fields=["description"],
            forbid_images_fields=["title", "purpose"],
            upload_to="project/images/",
            view="Project-images-detail",
            process_template=True,
            get_kwargs=lambda instance: {"project_id": instance.id},
            dry_run=dry_run,
        )
        self._handle_model(
            BlogEntry,
            images_fields=["content"],
            forbid_images_fields=["title"],
            upload_to="blog_entry/images/",
            view="BlogEntry-images-detail",
            process_template=True,
            get_kwargs=lambda instance: {"project_id": instance.project.id},
            dry_run=dry_run,
        )
        self._handle_model(
            Goal, forbid_images_fields=["title", "description"], dry_run=dry_run
        )
        self._handle_model(
            Location, forbid_images_fields=["title", "description"], dry_run=dry_run
        )
        self._handle_model(
            ProjectMessage,
            images_fields=["content"],
            upload_to="project_messages/images/",
            view="ProjectMessage-images-detail",
            get_kwargs=lambda instance: {"project_id": instance.project.id},
            get_owner=lambda instance: instance.author,
            dry_run=dry_run,
        )
        self._handle_model(
            ProjectTab,
            images_fields=["description"],
            forbid_images_fields=["title"],
            upload_to="project_tabs/images/",
            view="ProjectTab-images-detail",
            get_kwargs=lambda instance: {"project_id": instance.project.id},
            dry_run=dry_run,
        )
        self._handle_model(
            ProjectTabItem,
            images_fields=["content"],
            forbid_images_fields=["title"],
            upload_to="project_tab_items/images/",
            view="ProjectTabItem-images-detail",
            get_kwargs=lambda instance: {
                "project_id": instance.tab.project.id,
                "tab_id": instance.tab.id,
            },
            dry_run=dry_run,
        )
        self._handle_model(
            TagClassification,
            forbid_images_fields=["description", "title"],
            dry_run=dry_run,
        )
        self._handle_model(
            MentoringMessage, forbid_images_fields=["content"], dry_run=dry_run
        )
