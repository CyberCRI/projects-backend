from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from apps.commons.test import JwtAPITestCase
from apps.files.factories import AttachmentLinkFactory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import (
    BlogEntryFactory,
    ProjectFactory,
    ProjectTabFactory,
    ProjectTabItemFactory,
)
from apps.projects.models import Project, ProjectTab


@override_settings(API_KEY="test-api-key", API_KEY_HEADER_NAME="X-API-Key")
class ProjectAIEvaluationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[OrganizationFactory()],
            title="My project",
            description='<h2>Problem</h2><p>Kids & <a href="https://a.org">x</a></p>',
        )
        cls.tab = ProjectTabFactory(
            project=cls.project, title="Our team", type=ProjectTab.TabType.TEXT
        )
        ProjectTabItemFactory(tab=cls.tab, title="Item", content="<p>Item body</p>")
        BlogEntryFactory(project=cls.project, title="First post")
        BlogEntryFactory(project=cls.project, title="Second post")
        AttachmentLinkFactory(project=cls.project, site_url="https://b.org")
        cls.url = reverse("AIEvaluation-evaluate", args=(cls.project.id,))

    def payload(self, **kwargs):
        return {
            "system": ["You review {{ project.title }}."],
            "prompts": ["{{ project.description }}"],
            "json_schema": {
                "type": "object",
                "properties": {"passed": {"type": "boolean"}},
                "required": ["passed"],
                "additionalProperties": False,
            },
            **kwargs,
        }

    def test_requires_api_key(self):
        response = self.client.post(self.url, self.payload(), format="json")
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )
        response = self.client.post(
            self.url, self.payload(), format="json", headers={"X-API-Key": "wrong"}
        )
        self.assertIn(
            response.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    @patch(
        "services.mistral.interface.MistralService.get_structured_chat_response",
        return_value={"passed": True},
    )
    def test_renders_prompts_and_returns_llm_answer(self, mocked):
        tab_key = self.tab.slug.replace("-", "_")
        prompt = (
            "TAB: {{ project.tabs.%s.title }}\n"
            "{%% for item in project.tabs.%s.items %%}{{ item.content }}\n{%% endfor %%}"
            "{%% for entry in project.blog_entries %%}- {{ entry.title }}\n{%% endfor %%}"
            "{%% for link in project.attached_links %%}{{ link.url }}{%% endfor %%}"
        ) % (tab_key, tab_key)
        response = self.client.post(
            self.url,
            self.payload(prompts=["{{ project.description }}", prompt]),
            format="json",
            headers={"X-API-Key": "test-api-key"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"passed": True})

        system, prompts, schema = mocked.call_args.args
        self.assertEqual(system, ["You review My project."])
        self.assertEqual(prompts[0], "## Problem\nKids & x (https://a.org)")
        self.assertIn("TAB: Our team\nItem body", prompts[1])
        self.assertIn("- Second post\n- First post", prompts[1])
        self.assertIn("https://b.org", prompts[1])
        self.assertEqual(
            schema,
            {
                "type": "object",
                "properties": {"passed": {"type": "boolean"}},
                "required": ["passed"],
                "additionalProperties": False,
            },
        )

    @patch(
        "services.mistral.interface.MistralService.get_structured_chat_response",
        return_value={"passed": "yes"},
    )
    def test_llm_answer_not_matching_schema(self, mocked):
        response = self.client.post(
            self.url,
            self.payload(),
            format="json",
            headers={"X-API-Key": "test-api-key"},
        )
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

    @patch(
        "services.mistral.interface.MistralService.get_structured_chat_response",
        side_effect=RuntimeError(),
    )
    def test_llm_failure(self, mocked):
        response = self.client.post(
            self.url,
            self.payload(),
            format="json",
            headers={"X-API-Key": "test-api-key"},
        )
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)

    def test_invalid_payloads(self):
        for payload in [
            self.payload(prompts=["{% for x in %}"]),
            self.payload(prompts=['{% include "x.html" %}']),
            self.payload(prompts=[]),
            self.payload(json_schema={"type": "nope"}),
        ]:
            response = self.client.post(
                self.url,
                payload,
                format="json",
                headers={"X-API-Key": "test-api-key"},
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_project(self):
        url = reverse("AIEvaluation-evaluate", args=("unknown",))
        response = self.client.post(
            url,
            self.payload(),
            format="json",
            headers={"X-API-Key": "test-api-key"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
