from typing import Dict, List, Optional, Union

from faker import Faker

from apps.commons.test import JwtAPITestCase
from services.esco.models import EscoTag

faker = Faker()


class EscoTestCase(JwtAPITestCase):
    def search_skills_return_value(self, uris: List[str]) -> List[Dict[str, str]]:
        return [{"type": "skill", "uri": uri} for uri in uris]

    def search_occupations_return_value(self, uris: List[str]) -> List[Dict[str, str]]:
        return [{"type": "occupation", "uri": uri} for uri in uris]

    @classmethod
    def get_skill_return_value(
        cls,
        uri: str = "",
        title_en: str = "",
        title_fr: str = "",
        description_en: str = "",
        description_fr: str = "",
        broader_skills: Optional[List[EscoTag]] = None,
        essential_for_skills: Optional[List[EscoTag]] = None,
        optional_for_skills: Optional[List[EscoTag]] = None,
    ) -> Dict[str, Union[str, Dict]]:
        uri = uri or faker.url()
        title_en = title_en or faker.sentence()
        title_fr = title_fr or faker.sentence()
        description_en = description_en or faker.text()
        description_fr = description_fr or faker.text()
        broader_skills = broader_skills or []
        essential_for_skills = essential_for_skills or []
        optional_for_skills = optional_for_skills or []
        return {
            "className": "Skill",
            "classId": "http://data.europa.eu/esco/model#Skill",
            "uri": uri,
            "title": title_en,
            "referenceLanguage": ["en"],
            "preferredLabel": {
                "fr": title_fr,
                "en": title_en,
            },
            "description": {
                "fr": {"literal": description_fr, "mimetype": "plain/text"},
                "en": {"literal": description_en, "mimetype": "plain/text"},
            },
            "status": "released",
            "_links": {
                "self": {
                    "href": f"https://ec.europa.eu/esco/api/resource/skill?uri={uri}&language=en",
                    "uri": uri,
                    "title": title_en,
                },
                "broaderSkill": [
                    {
                        "href": f"https://ec.europa.eu/esco/api/resource/skill?uri={skill.uri}&language=en",
                        "uri": skill.uri,
                        "title": skill.title,
                        "skillType": "http://data.europa.eu/esco/skill-type/skill",
                    }
                    for skill in broader_skills
                ],
                "isOptionalForSkill": [
                    {
                        "href": f"https://ec.europa.eu/esco/api/resource/skill?uri={skill.uri}&language=en",
                        "uri": skill.uri,
                        "title": skill.title,
                        "skillType": "http://data.europa.eu/esco/skill-type/skill",
                    }
                    for skill in optional_for_skills
                ],
                "isEssentialForSkill": [
                    {
                        "href": f"https://ec.europa.eu/esco/api/resource/skill?uri={skill.uri}&language=en",
                        "uri": skill.uri,
                        "title": skill.title,
                        "skillType": "http://data.europa.eu/esco/skill-type/skill",
                    }
                    for skill in essential_for_skills
                ],
            },
        }

    @classmethod
    def get_occupation_return_value(
        cls,
        uri: str = "",
        title_en: str = "",
        title_fr: str = "",
        description_en: str = "",
        description_fr: str = "",
        broader_occupations: Optional[List[EscoTag]] = None,
        essential_skills: Optional[List[EscoTag]] = None,
        optional_skills: Optional[List[EscoTag]] = None,
    ) -> Dict[str, Union[str, Dict]]:
        uri = uri or faker.url()
        title_en = title_en or faker.sentence()
        title_fr = title_fr or faker.sentence()
        description_en = description_en or faker.text()
        description_fr = description_fr or faker.text()
        broader_occupations = broader_occupations or []
        essential_skills = essential_skills or []
        optional_skills = optional_skills or []
        return {
            "className": "Occupation",
            "classId": "http://data.europa.eu/esco/model#Occupation",
            "uri": uri,
            "title": title_en,
            "referenceLanguage": ["en"],
            "preferredLabel": {
                "fr": f"{title_fr} preferred",
                "en": title_en,
            },
            "alternativeTerms": {
                "fr": [
                    {"roles": ["male"], "label": title_fr},
                    {"roles": ["female"], "label": f"{title_fr} female"},
                ],
            },
            "description": {
                "fr": {"literal": description_fr, "mimetype": "plain/text"},
                "en": {"literal": description_en, "mimetype": "plain/text"},
            },
            "status": "released",
            "_links": {
                "self": {
                    "href": f"https://ec.europa.eu/esco/api/resource/occupation?uri={uri}&language=en",
                    "uri": uri,
                    "title": title_en,
                },
                "hasEssentialSkill": [
                    {
                        "href": f"https://ec.europa.eu/esco/api/resource/skill?uri={skill.uri}&language=en",
                        "uri": skill.uri,
                        "title": skill.title,
                        "skillType": "http://data.europa.eu/esco/skill-type/skill",
                    }
                    for skill in essential_skills
                ],
                "hasOptionalSkill": [
                    {
                        "href": f"https://ec.europa.eu/esco/api/resource/skill?uri={skill.uri}&language=en",
                        "uri": skill.uri,
                        "title": skill.title,
                        "skillType": "http://data.europa.eu/esco/skill-type/skill",
                    }
                    for skill in optional_skills
                ],
                "broaderOccupation": [
                    {
                        "href": f"https://ec.europa.eu/esco/api/resource/occupation?uri={occupation.uri}&language=en",
                        "uri": occupation.uri,
                        "title": occupation.title,
                    }
                    for occupation in broader_occupations
                ],
            },
        }

    def raise_exception_side_effect(self, *args, **kwargs):
        raise Exception()
