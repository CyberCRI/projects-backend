from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.search.models import SearchObject
from apps.search.tasks import clean_duplicate_search_objects


class ProjectIndexUpdateSignalTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])
        cls.people_group = PeopleGroupFactory(organization=cls.organization)
        cls.user = UserFactory()

    def test_clean_duplicate_search_objects(self):
        self.assertEqual(SearchObject.objects.count(), 0)
        for _ in range(3):
            SearchObject.objects.create(
                type=SearchObject.SearchObjectType.PROJECT,
                project=self.project,
            )
            SearchObject.objects.create(
                type=SearchObject.SearchObjectType.PEOPLE_GROUP,
                people_group=self.people_group,
            )
            SearchObject.objects.create(
                type=SearchObject.SearchObjectType.USER,
                user=self.user,
            )
        self.assertEqual(SearchObject.objects.count(), 9)
        clean_duplicate_search_objects()
        self.assertEqual(SearchObject.objects.count(), 3)
        self.assertEqual(
            SearchObject.objects.filter(
                type=SearchObject.SearchObjectType.PROJECT, project=self.project
            ).count(),
            1,
        )
        self.assertEqual(
            SearchObject.objects.filter(
                type=SearchObject.SearchObjectType.PEOPLE_GROUP,
                people_group=self.people_group,
            ).count(),
            1,
        )
        self.assertEqual(
            SearchObject.objects.filter(
                type=SearchObject.SearchObjectType.USER, user=self.user
            ).count(),
            1,
        )
