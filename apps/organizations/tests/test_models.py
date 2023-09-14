from rest_framework.exceptions import ValidationError

from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory


class OrganizationModelTestCase(JwtAPITestCase):
    def test_parent_cannot_be_itself(self):
        organization = OrganizationFactory()
        organization.parent = organization
        self.assertRaises(ValidationError, lambda: organization.save())
