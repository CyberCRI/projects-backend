from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.commons.test import JwtAPITestCase
from apps.files import tasks
from apps.files.models import Image
from apps.organizations.factories import OrganizationFactory


class DeleteOrphanImagesTestCase(JwtAPITestCase):
    def test_delete_orphan_images(self):
        orphan = self.get_test_image()
        orphan_outdated = self.get_test_image()
        linked = self.get_test_image()
        linked_outdated = self.get_test_image()

        date = timezone.now() - timedelta(
            seconds=settings.IMAGE_ORPHAN_THRESHOLD_SECONDS
        )
        orphan_outdated.created_at = date
        orphan_outdated.save()
        linked_outdated.created_at = date
        linked_outdated.save()

        OrganizationFactory(banner_image=linked, logo_image=linked_outdated)

        orphan_outdated_pk = orphan_outdated.pk
        subset = {orphan.pk, linked.pk, linked_outdated.pk}
        deleted = tasks.delete_orphan_images()
        image_set = set(Image.objects.values_list("pk", flat=True))

        self.assertEqual(deleted, [orphan_outdated_pk])
        self.assertNotIn(orphan_outdated_pk, image_set)
        self.assertTrue(subset.issubset(image_set))
