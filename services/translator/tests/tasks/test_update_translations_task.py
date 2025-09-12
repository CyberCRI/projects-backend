from typing import Dict, List
from unittest.mock import call, patch

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
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
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
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

faker = Faker()


class UpdateTranslationsTestCase(JwtAPITestCase):
    @classmethod
    def translator_side_effect(
        cls, body: List[str], to_language: List[str]
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
        - A json response that simulates the Azure translator API response.
        """

        return [
            {
                "detectedLanguage": {"language": "en", "score": 1.0},
                "translations": [
                    {"text": f"{lang} : {body[0]}", "to": lang} for lang in to_language
                ],
            }
        ]

    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization_data = {
            field: faker.word() for field in Organization.auto_translated_fields
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
            field: faker.word() for field in ProjectUser.auto_translated_fields
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
            field: faker.word() for field in Project.auto_translated_fields
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
        ]:
            model = factory._meta.model
            data = {field: faker.word() for field in model.auto_translated_fields}
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
            data = {field: faker.word() for field in model.auto_translated_fields}
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
            field: faker.word()
            for field in MentoringMessageFactory._meta.model.auto_translated_fields
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
            field: faker.word()
            for field in ProjectTabItemFactory._meta.model.auto_translated_fields
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
    def test_update_project_translated_fields(self, mock_translate):
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
                    body=[getattr(instance, field)],
                    to_language=[str(lang) for lang in self.organization_1.languages],
                )
                for instance, field in [
                    *[
                        (data["instance_1"], field)
                        for data in self.instances
                        for field in data["model"].auto_translated_fields
                    ],
                ]
            ]
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
                for field in data["model"].auto_translated_fields:
                    self.assertEqual(getattr(instance, field), data["data"][field])

            # Translated fields must be correctly set for instance_1
            instance = data["instance_1"]
            for field in data["model"].auto_translated_fields:
                self.assertEqual(getattr(instance, f"{field}_detected_language"), "en")
            for lang in settings.REQUIRED_LANGUAGES:
                if lang in self.organization_1.languages:
                    for field in data["model"].auto_translated_fields:
                        self.assertEqual(
                            getattr(instance, f"{field}_{lang}"),
                            f"{lang} : {data['data'][field]}",
                        )
                else:
                    for field in data["model"].auto_translated_fields:
                        self.assertEqual(getattr(instance, f"{field}_{lang}") or "", "")

            # Translated fields must be empty for instance_2 and instance_3
            for instance in [data["instance_2"], data["instance_3"]]:
                for lang in settings.REQUIRED_LANGUAGES:
                    for field in data["model"].auto_translated_fields:
                        self.assertEqual(getattr(instance, f"{field}_{lang}") or "", "")
