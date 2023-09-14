from django.test import TestCase

from apps.files.serializers import AttachmentLinkSerializer
from apps.projects.factories import ProjectFactory


class AttachmentLinkSerializerTestCase(TestCase):
    def test_site_url_unreachable(self):
        project = ProjectFactory()
        data = {"project_id": project.id, "site_url": "https://unreachable.unreachable"}
        serializer = AttachmentLinkSerializer(data=data)
        assert serializer.is_valid()
