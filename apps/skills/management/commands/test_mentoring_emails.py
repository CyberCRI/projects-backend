import requests
from django.core.management import BaseCommand
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import SeedUserFactory
from apps.organizations.models import Organization
from apps.skills.factories import (
    MentorCreatedMentoringFactory,
    MentoreeCreatedMentoringFactory,
    SkillFactory,
)
from apps.skills.models import Mentoring
from services.keycloak.interface import KeycloakService

faker = Faker()


class Command(BaseCommand):
    """
    Send all emails as test for debugging mentoring.
    """

    def handle(self, *args, **options):
        organization = Organization.objects.get(code="CRI")
        french_user = SeedUserFactory(language="fr")
        english_user = SeedUserFactory(language="en")
        french_token = KeycloakService.get_token_for_user(
            french_user.keycloak_account.username, "password"
        )
        french_token = french_token["access_token"]
        english_token = KeycloakService.get_token_for_user(
            english_user.keycloak_account.username, "password"
        )
        english_token = english_token["access_token"]

        # english needs french as mentor
        skill = SkillFactory(user=french_user, can_mentor=True)
        payload = {
            "content": "English needs French as mentor"
            "\nwith line break\n\nwith double line break",
            "reply_to": faker.email(),
        }
        response = requests.post(
            "http://localhost:8000"
            + reverse(
                "Mentoring-contact-mentor",
                args=(
                    organization.code,
                    skill.id,
                ),
            ),
            data=payload,
            headers={"Authorization": f"Bearer {english_token}"},
            timeout=10,
        )
        assert response.status_code == status.HTTP_200_OK

        # french needs english as mentor
        skill = SkillFactory(user=english_user, can_mentor=True)
        payload = {
            "content": "French needs English as mentor"
            "\nwith line break\n\nwith double line break",
            "reply_to": faker.email(),
        }
        response = requests.post(
            "http://localhost:8000"
            + reverse(
                "Mentoring-contact-mentor",
                args=(
                    organization.code,
                    skill.id,
                ),
            ),
            data=payload,
            headers={"Authorization": f"Bearer {french_token}"},
            timeout=10,
        )
        assert response.status_code == status.HTTP_200_OK

        # english needs french as mentoree
        skill = SkillFactory(user=french_user, needs_mentor=True)
        payload = {
            "content": "English needs French as mentoree"
            "\nwith line break\n\nwith double line break",
            "reply_to": faker.email(),
        }
        response = requests.post(
            "http://localhost:8000"
            + reverse(
                "Mentoring-contact-mentoree",
                args=(
                    organization.code,
                    skill.id,
                ),
            ),
            data=payload,
            headers={"Authorization": f"Bearer {english_token}"},
            timeout=10,
        )
        assert response.status_code == status.HTTP_200_OK

        # french needs english as mentoree
        skill = SkillFactory(user=english_user, needs_mentor=True)
        payload = {
            "content": "French needs English as mentoree"
            "\nwith line break\n\nwith double line break",
            "reply_to": faker.email(),
        }
        response = requests.post(
            "http://localhost:8000"
            + reverse(
                "Mentoring-contact-mentoree",
                args=(
                    organization.code,
                    skill.id,
                ),
            ),
            data=payload,
            headers={"Authorization": f"Bearer {french_token}"},
            timeout=10,
        )
        assert response.status_code == status.HTTP_200_OK

        # french needs more info from english mentor request
        mentoring = MentoreeCreatedMentoringFactory(
            organization=organization, mentor=french_user, mentoree=english_user
        )
        payload = {
            "status": Mentoring.MentoringStatus.PENDING.value,
            "content": "French needs more info from English mentor request"
            "\nwith line break\n\nwith double line break",
            "reply_to": faker.email(),
        }
        response = requests.post(
            "http://localhost:8000"
            + reverse(
                "Mentoring-respond",
                args=(
                    organization.code,
                    mentoring.id,
                ),
            ),
            data=payload,
            headers={"Authorization": f"Bearer {french_token}"},
            timeout=10,
        )
        assert response.status_code == status.HTTP_200_OK

        # english needs more info from french mentor request
        mentoring = MentoreeCreatedMentoringFactory(
            organization=organization, mentor=english_user, mentoree=french_user
        )
        payload = {
            "status": Mentoring.MentoringStatus.PENDING.value,
            "content": "English needs more info from French mentor request"
            "\nwith line break\n\nwith double line break",
            "reply_to": faker.email(),
        }
        response = requests.post(
            "http://localhost:8000"
            + reverse(
                "Mentoring-respond",
                args=(
                    organization.code,
                    mentoring.id,
                ),
            ),
            data=payload,
            headers={"Authorization": f"Bearer {english_token}"},
            timeout=10,
        )
        assert response.status_code == status.HTTP_200_OK

        # french needs more info from english mentoree request
        mentoring = MentorCreatedMentoringFactory(
            organization=organization, mentor=english_user, mentoree=french_user
        )
        payload = {
            "status": Mentoring.MentoringStatus.PENDING.value,
            "content": "French needs more info from English mentoree request"
            "\nwith line break\n\nwith double line break",
            "reply_to": faker.email(),
        }
        response = requests.post(
            "http://localhost:8000"
            + reverse(
                "Mentoring-respond",
                args=(
                    organization.code,
                    mentoring.id,
                ),
            ),
            data=payload,
            headers={"Authorization": f"Bearer {french_token}"},
            timeout=10,
        )
        assert response.status_code == status.HTTP_200_OK

        # english needs more info from french mentoree request
        mentoring = MentorCreatedMentoringFactory(
            organization=organization, mentor=french_user, mentoree=english_user
        )
        payload = {
            "status": Mentoring.MentoringStatus.PENDING.value,
            "content": "English needs more info from French mentoree request"
            "\nwith line break\n\nwith double line break",
            "reply_to": faker.email(),
        }
        response = requests.post(
            "http://localhost:8000"
            + reverse(
                "Mentoring-respond",
                args=(
                    organization.code,
                    mentoring.id,
                ),
            ),
            data=payload,
            headers={"Authorization": f"Bearer {english_token}"},
            timeout=10,
        )
        assert response.status_code == status.HTTP_200_OK

        # french accepts english mentor request
        mentoring = MentoreeCreatedMentoringFactory(
            organization=organization, mentor=french_user, mentoree=english_user
        )
        payload = {
            "status": Mentoring.MentoringStatus.ACCEPTED.value,
            "content": "French accepts English mentor request"
            "\nwith line break\n\nwith double line break",
            "reply_to": faker.email(),
        }
        response = requests.post(
            "http://localhost:8000"
            + reverse(
                "Mentoring-respond",
                args=(
                    organization.code,
                    mentoring.id,
                ),
            ),
            data=payload,
            headers={"Authorization": f"Bearer {french_token}"},
            timeout=10,
        )
        assert response.status_code == status.HTTP_200_OK

        # english accepts french mentor request
        mentoring = MentoreeCreatedMentoringFactory(
            organization=organization, mentor=english_user, mentoree=french_user
        )
        payload = {
            "status": Mentoring.MentoringStatus.ACCEPTED.value,
            "content": "English accepts French mentor request"
            "\nwith line break\n\nwith double line break",
            "reply_to": faker.email(),
        }
        response = requests.post(
            "http://localhost:8000"
            + reverse(
                "Mentoring-respond",
                args=(
                    organization.code,
                    mentoring.id,
                ),
            ),
            data=payload,
            headers={"Authorization": f"Bearer {english_token}"},
            timeout=10,
        )
        assert response.status_code == status.HTTP_200_OK

        # french accepts english mentoree request
        mentoring = MentorCreatedMentoringFactory(
            organization=organization, mentor=english_user, mentoree=french_user
        )
        payload = {
            "status": Mentoring.MentoringStatus.ACCEPTED.value,
            "content": "French accepts English mentoree request"
            "\nwith line break\n\nwith double line break",
            "reply_to": faker.email(),
        }
        response = requests.post(
            "http://localhost:8000"
            + reverse(
                "Mentoring-respond",
                args=(
                    organization.code,
                    mentoring.id,
                ),
            ),
            data=payload,
            headers={"Authorization": f"Bearer {french_token}"},
            timeout=10,
        )
        assert response.status_code == status.HTTP_200_OK

        # english accepts french mentoree request
        mentoring = MentorCreatedMentoringFactory(
            organization=organization, mentor=french_user, mentoree=english_user
        )
        payload = {
            "status": Mentoring.MentoringStatus.ACCEPTED.value,
            "content": "English accepts French mentoree request"
            "\nwith line break\n\nwith double line break",
            "reply_to": faker.email(),
        }
        response = requests.post(
            "http://localhost:8000"
            + reverse(
                "Mentoring-respond",
                args=(
                    organization.code,
                    mentoring.id,
                ),
            ),
            data=payload,
            headers={"Authorization": f"Bearer {english_token}"},
            timeout=10,
        )
        assert response.status_code == status.HTTP_200_OK

        # french rejects english mentor request
        mentoring = MentoreeCreatedMentoringFactory(
            organization=organization, mentor=french_user, mentoree=english_user
        )
        payload = {
            "status": Mentoring.MentoringStatus.REJECTED.value,
            "content": "French rejects English mentor request"
            "\nwith line break\n\nwith double line break",
            "reply_to": faker.email(),
        }
        response = requests.post(
            "http://localhost:8000"
            + reverse(
                "Mentoring-respond",
                args=(
                    organization.code,
                    mentoring.id,
                ),
            ),
            data=payload,
            headers={"Authorization": f"Bearer {french_token}"},
            timeout=10,
        )
        assert response.status_code == status.HTTP_200_OK

        # english rejects french mentor request
        mentoring = MentoreeCreatedMentoringFactory(
            organization=organization, mentor=english_user, mentoree=french_user
        )
        payload = {
            "status": Mentoring.MentoringStatus.REJECTED.value,
            "content": "English rejects French mentor request"
            "\nwith line break\n\nwith double line break",
            "reply_to": faker.email(),
        }
        response = requests.post(
            "http://localhost:8000"
            + reverse(
                "Mentoring-respond",
                args=(
                    organization.code,
                    mentoring.id,
                ),
            ),
            data=payload,
            headers={"Authorization": f"Bearer {english_token}"},
            timeout=10,
        )
        assert response.status_code == status.HTTP_200_OK

        # french rejects english mentoree request
        mentoring = MentorCreatedMentoringFactory(
            organization=organization, mentor=english_user, mentoree=french_user
        )
        payload = {
            "status": Mentoring.MentoringStatus.REJECTED.value,
            "content": "French rejects English mentoree request"
            "\nwith line break\n\nwith double line break",
            "reply_to": faker.email(),
        }
        response = requests.post(
            "http://localhost:8000"
            + reverse(
                "Mentoring-respond",
                args=(
                    organization.code,
                    mentoring.id,
                ),
            ),
            data=payload,
            headers={"Authorization": f"Bearer {french_token}"},
            timeout=10,
        )
        assert response.status_code == status.HTTP_200_OK

        # english rejects french mentoree request
        mentoring = MentorCreatedMentoringFactory(
            organization=organization, mentor=french_user, mentoree=english_user
        )
        payload = {
            "status": Mentoring.MentoringStatus.REJECTED.value,
            "content": "English rejects French mentoree request"
            "\nwith line break\n\nwith double line break",
            "reply_to": faker.email(),
        }
        response = requests.post(
            "http://localhost:8000"
            + reverse(
                "Mentoring-respond",
                args=(
                    organization.code,
                    mentoring.id,
                ),
            ),
            data=payload,
            headers={"Authorization": f"Bearer {english_token}"},
            timeout=10,
        )
        assert response.status_code == status.HTTP_200_OK
