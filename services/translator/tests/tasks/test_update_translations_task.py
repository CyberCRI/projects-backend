from types import SimpleNamespace
from typing import Dict, List
from unittest.mock import call, patch

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import ProjectUser
from apps.announcements.factories import AnnouncementFactory
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import CommentFactory, ReviewFactory
from apps.files.factories import (
    AttachmentFileFactory,
    AttachmentLinkFactory,
    OrganizationAttachmentFileFactory,
)
from apps.invitations.factories import AccessRequestFactory, InvitationFactory
from apps.newsfeed.factories import EventFactory, InstructionFactory, NewsFactory
from apps.organizations.factories import (
    OrganizationFactory,
    ProjectCategoryFactory,
    TemplateFactory,
)
from apps.organizations.models import Organization
from apps.projects.factories import (
    BlogEntryFactory,
    GoalFactory,
    LocationFactory,
    ProjectFactory,
    ProjectMessageFactory,
    ProjectTabFactory,
    ProjectTabItemFactory,
)
from apps.projects.models import Project
from apps.skills.factories import (
    MentorCreatedMentoringFactory,
    MentoringMessageFactory,
    TagClassificationFactory,
)
from services.translator.models import AutoTranslatedField
from services.translator.tasks import automatic_translations
from services.translator.utils import update_auto_translated_field

faker = Faker()


class MockTranslateTestCase(JwtAPITestCase):
    @classmethod
    def translator_side_effect(
        cls, body: List[str], to_language: List[str], text_type: str = "plain"
    ) -> List[Dict]:
        """
        This side effect is meant to be used with unittest mock. It will mock every call
        made to the Azure translator API.

        Arguments
        ---------
        - content (str): The text content to be translated.
        - languages (list of str): The target languages for translation.

        Returns
        -------
        - A list of SimpleNamespace objects that simulates the Azure translator API response.
        """

        return [
            SimpleNamespace(
                detected_language=SimpleNamespace(language="en", score=1.0),
                translations=[
                    SimpleNamespace(text=f"{lang} : {body[0]}", to=lang)
                    for lang in to_language
                ],
            )
        ]


class UpdateTranslationsTestCase(MockTranslateTestCase):

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization_data = {
            field: (
                f"<p>{faker.word()}</p>"
                if field in Organization._html_auto_translated_fields
                else faker.word()
            )
            for field in Organization._auto_translated_fields
        }
        cls.organization_1 = OrganizationFactory(
            auto_translate_content=True, **cls.organization_data
        )
        cls.organization_2 = OrganizationFactory(
            auto_translate_content=True, **cls.organization_data
        )
        cls.organization_3 = OrganizationFactory(
            auto_translate_content=False, **cls.organization_data
        )
        cls.instances = [
            {
                "model": Organization,
                "data": cls.organization_data,
                "instance_1": cls.organization_1,
                "instance_2": cls.organization_2,
                "instance_3": cls.organization_3,
            }
        ]

        cls.user_data = {
            field: (
                f"<p>{faker.word()}</p>"
                if field in ProjectUser._html_auto_translated_fields
                else faker.word()
            )
            for field in ProjectUser._auto_translated_fields
        }
        cls.user_1 = UserFactory(
            groups=[cls.organization_1.get_users()], **cls.user_data
        )
        cls.user_2 = UserFactory(
            groups=[cls.organization_2.get_users()], **cls.user_data
        )
        cls.user_3 = UserFactory(
            groups=[cls.organization_3.get_users()], **cls.user_data
        )
        cls.instances.append(
            {
                "model": ProjectUser,
                "data": cls.user_data,
                "instance_1": cls.user_1,
                "instance_2": cls.user_2,
                "instance_3": cls.user_3,
            }
        )

        cls.project_data = {
            field: (
                f"<p>{faker.word()}</p>"
                if field in Project._html_auto_translated_fields
                else faker.word()
            )
            for field in Project._auto_translated_fields
        }
        cls.project_1 = ProjectFactory(
            organizations=[cls.organization_1], **cls.project_data
        )
        cls.project_2 = ProjectFactory(
            organizations=[cls.organization_2], **cls.project_data
        )
        cls.project_3 = ProjectFactory(
            organizations=[cls.organization_3], **cls.project_data
        )
        cls.instances.append(
            {
                "model": Project,
                "data": cls.project_data,
                "instance_1": cls.project_1,
                "instance_2": cls.project_2,
                "instance_3": cls.project_3,
            }
        )

        # Create instances for models related to organizations
        for factory in [
            PeopleGroupFactory,
            OrganizationAttachmentFileFactory,
            InvitationFactory,
            AccessRequestFactory,
            NewsFactory,
            InstructionFactory,
            EventFactory,
            ProjectCategoryFactory,
            TagClassificationFactory,
            TemplateFactory,
        ]:
            model = factory._meta.model
            data = {
                field: (
                    f"<p>{faker.word()}</p>"
                    if field in model._html_auto_translated_fields
                    else faker.word()
                )
                for field in model._auto_translated_fields
            }
            instance_1 = factory(organization=cls.organization_1, **data)
            instance_2 = factory(organization=cls.organization_2, **data)
            instance_3 = factory(organization=cls.organization_3, **data)
            cls.instances.append(
                {
                    "model": model,
                    "data": data,
                    "instance_1": instance_1,
                    "instance_2": instance_2,
                    "instance_3": instance_3,
                }
            )

        # Create instances for models related to projects
        for factory in [
            AnnouncementFactory,
            CommentFactory,
            ReviewFactory,
            AttachmentLinkFactory,
            AttachmentFileFactory,
            BlogEntryFactory,
            GoalFactory,
            LocationFactory,
            ProjectMessageFactory,
            ProjectTabFactory,
        ]:
            model = factory._meta.model
            data = {
                field: (
                    f"<p>{faker.word()}</p>"
                    if field in model._html_auto_translated_fields
                    else faker.word()
                )
                for field in model._auto_translated_fields
            }
            instance_1 = factory(project=cls.project_1, **data)
            instance_2 = factory(project=cls.project_2, **data)
            instance_3 = factory(project=cls.project_3, **data)
            cls.instances.append(
                {
                    "model": model,
                    "data": data,
                    "instance_1": instance_1,
                    "instance_2": instance_2,
                    "instance_3": instance_3,
                }
            )

        # MentoringMessage has indirect relation to organizations through Mentoring
        mentoring_1 = MentorCreatedMentoringFactory(
            organization=cls.organization_1, mentor=cls.user_1, mentoree=cls.user_1
        )
        mentoring_2 = MentorCreatedMentoringFactory(
            organization=cls.organization_2, mentor=cls.user_2, mentoree=cls.user_2
        )
        mentoring_3 = MentorCreatedMentoringFactory(
            organization=cls.organization_3, mentor=cls.user_3, mentoree=cls.user_3
        )
        data = {
            field: (
                f"<p>{faker.word()}</p>"
                if field
                in MentoringMessageFactory._meta.model._html_auto_translated_fields
                else faker.word()
            )
            for field in MentoringMessageFactory._meta.model._auto_translated_fields
        }
        cls.instances.append(
            {
                "model": MentoringMessageFactory._meta.model,
                "data": data,
                "instance_1": MentoringMessageFactory(
                    mentoring=mentoring_1, sender=cls.user_1, **data
                ),
                "instance_2": MentoringMessageFactory(
                    mentoring=mentoring_2, sender=cls.user_2, **data
                ),
                "instance_3": MentoringMessageFactory(
                    mentoring=mentoring_3, sender=cls.user_3, **data
                ),
            }
        )

        # ProjectTabItem has indirect relation to organizations through ProjectTab
        tabs = [
            i for i in cls.instances if i["model"] == ProjectTabFactory._meta.model
        ][0]
        data = {
            field: (
                f"<p>{faker.word()}</p>"
                if field
                in ProjectTabItemFactory._meta.model._html_auto_translated_fields
                else faker.word()
            )
            for field in ProjectTabItemFactory._meta.model._auto_translated_fields
        }
        cls.instances.append(
            {
                "model": ProjectTabItemFactory._meta.model,
                "data": data,
                "instance_1": ProjectTabItemFactory(tab=tabs["instance_1"], **data),
                "instance_2": ProjectTabItemFactory(tab=tabs["instance_2"], **data),
                "instance_3": ProjectTabItemFactory(tab=tabs["instance_3"], **data),
            }
        )

    @patch("azure.ai.translation.text.TextTranslationClient.translate")
    def test_update_translated_fields(self, mock_translate):
        """
        This test is fully automated, do not directly update it unless you know what
        you are doing.

        To add new models to be tested, add them to the `self.instances` list in the
        `setUpTestData` class method instead of modifying this test with the following
        structure:

        ```
        {
            "model": The model class,
            "data": A dict with the translated fields and their initial values,
            "instance_1": An instance of the model related to organization_1,
            "instance_2": An instance of the model related to organization_2,
            "instance_3": An instance of the model related to organization_3,
        }
        ```
        """
        mock_translate.side_effect = self.translator_side_effect

        # Mark all fields as up to date to remove noise
        AutoTranslatedField.objects.update(up_to_date=True)

        # Mark some fields as not up to date (instance 1 and 3 of each model)
        for data in self.instances:
            AutoTranslatedField.objects.filter(
                content_type=ContentType.objects.get_for_model(data["model"]),
                object_id__in=[data["instance_1"].pk, data["instance_3"].pk],
            ).update(up_to_date=False)

        # Run the automatic translations task
        automatic_translations()

        # Check that the mock was called with the expected parameters
        mock_translate.assert_has_calls(
            [
                call(
                    body=[
                        getattr(
                            instance, field.split(":", 1)[1] if ":" in field else field
                        )
                    ],
                    to_language={str(lang) for lang in self.organization_1.languages},
                    text_type=(field.split(":", 1)[0] if ":" in field else "plain"),
                )
                for instance, field in [
                    *[
                        (data["instance_1"], field)
                        for data in self.instances
                        for field in data["model"].auto_translated_fields
                    ],
                ]
            ],
            any_order=True,
        )

        # Check that all fields are now up to date
        self.assertEqual(
            AutoTranslatedField.objects.filter(up_to_date=False).count(), 0
        )

        # Check that the translations were correctly applied
        for data in self.instances:
            # Initial fields must be unchanged
            for instance in [
                data["instance_1"],
                data["instance_2"],
                data["instance_3"],
            ]:
                instance.refresh_from_db()
                for field in data["model"]._auto_translated_fields:
                    self.assertEqual(getattr(instance, field), data["data"][field])

            # Translated fields must be correctly set for instance_1
            instance = data["instance_1"]
            for field in data["model"]._auto_translated_fields:
                self.assertEqual(getattr(instance, f"{field}_detected_language"), "en")
            for lang in settings.REQUIRED_LANGUAGES:
                if lang in self.organization_1.languages:
                    for field in data["model"]._auto_translated_fields:
                        self.assertEqual(
                            getattr(instance, f"{field}_{lang}"),
                            f"{lang} : {data['data'][field]}",
                        )
                else:
                    for field in data["model"]._auto_translated_fields:
                        self.assertEqual(getattr(instance, f"{field}_{lang}") or "", "")

            # Translated fields must be empty for instance_2 and instance_3
            for instance in [data["instance_2"], data["instance_3"]]:
                for lang in settings.REQUIRED_LANGUAGES:
                    for field in data["model"]._auto_translated_fields:
                        self.assertEqual(getattr(instance, f"{field}_{lang}") or "", "")


class MiscTranslationTestCase(MockTranslateTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory(
            auto_translate_content=True, languages=["fr", "en"]
        )

    @patch("azure.ai.translation.text.TextTranslationClient.translate")
    def test_safe_translation_with_base64_image(self, mock_translate):
        mock_translate.side_effect = self.translator_side_effect

        text = f"<div>{self.get_base64_image()}</div>"
        project = ProjectFactory(organizations=[self.organization], description=text)
        field = AutoTranslatedField.objects.get(
            content_type=ContentType.objects.get_for_model(Project),
            object_id=project.pk,
            field_name="description",
        )

        update_auto_translated_field(field)
        mock_translate.assert_has_calls([])

    @patch("azure.ai.translation.text.TextTranslationClient.translate")
    def test_split_content_html(self, mock_translate):
        mock_translate.side_effect = self.translator_side_effect

        project = ProjectFactory(organizations=[self.organization])
        image = self.get_test_image()
        project.images.add(image)
        image_path = reverse("Project-images-detail", args=(project.id, image.id))
        description = [
            f"<p>{faker.sentence()}</p>",  # One call for this chunk
            f'<img alt="alt" src="{image_path}"/>',
            f"<p>{'a' * 30000}</p>",  # Two calls for this chunk
            f'<p><img alt="alt" src="{image_path}"/></p>',
            f"<p>{'b' * 50000}</p>",  # Chunk too large, not translated
        ]
        project.description = "".join(description)
        project.save()
        field = AutoTranslatedField.objects.get(
            content_type=ContentType.objects.get_for_model(Project),
            object_id=project.pk,
            field_name="description",
        )
        update_auto_translated_field(field)
        mock_translate.assert_has_calls(
            [
                call(
                    body=[str(description[0])],
                    to_language={str(lang) for lang in self.organization.languages},
                    text_type="html",
                ),
                *[
                    call(
                        body=[str(description[2])],
                        to_language={str(lang)},
                        text_type="html",
                    )
                    for lang in self.organization.languages
                ],
            ],
            any_order=True,
        )
        project.refresh_from_db()
        for lang in self.organization.languages:
            self.assertEqual(
                getattr(project, f"description_{lang}"),
                f"{lang} : {description[0]}"
                f"{description[1]}"
                f"{lang} : {description[2]}"
                f"{description[3]}"
                f"{description[4]}",
            )
