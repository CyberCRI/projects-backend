import random
from typing import Dict, List, Optional, Union

from faker import Faker
from rest_framework import status

from apps.commons.test import JwtAPITestCase

from .models import Tag

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
        broader_skills: Optional[List[Tag]] = None,
        essential_for_skills: Optional[List[Tag]] = None,
        optional_for_skills: Optional[List[Tag]] = None,
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
                        "href": f"https://ec.europa.eu/esco/api/resource/skill?uri={skill.external_id}&language=en",
                        "uri": skill.external_id,
                        "title": skill.title,
                        "skillType": "http://data.europa.eu/esco/skill-type/skill",
                    }
                    for skill in broader_skills
                ],
                "isOptionalForSkill": [
                    {
                        "href": f"https://ec.europa.eu/esco/api/resource/skill?uri={skill.external_id}&language=en",
                        "uri": skill.external_id,
                        "title": skill.title,
                        "skillType": "http://data.europa.eu/esco/skill-type/skill",
                    }
                    for skill in optional_for_skills
                ],
                "isEssentialForSkill": [
                    {
                        "href": f"https://ec.europa.eu/esco/api/resource/skill?uri={skill.external_id}&language=en",
                        "uri": skill.external_id,
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
        broader_occupations: Optional[List[Tag]] = None,
        essential_skills: Optional[List[Tag]] = None,
        optional_skills: Optional[List[Tag]] = None,
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
                        "href": f"https://ec.europa.eu/esco/api/resource/skill?uri={skill.external_id}&language=en",
                        "uri": skill.external_id,
                        "title": skill.title,
                        "skillType": "http://data.europa.eu/esco/skill-type/skill",
                    }
                    for skill in essential_skills
                ],
                "hasOptionalSkill": [
                    {
                        "href": f"https://ec.europa.eu/esco/api/resource/skill?uri={skill.external_id}&language=en",
                        "uri": skill.external_id,
                        "title": skill.title,
                        "skillType": "http://data.europa.eu/esco/skill-type/skill",
                    }
                    for skill in optional_skills
                ],
                "broaderOccupation": [
                    {
                        "href": f"https://ec.europa.eu/esco/api/resource/occupation?uri={occupation.external_id}&language=en",
                        "uri": occupation.external_id,
                        "title": occupation.title,
                    }
                    for occupation in broader_occupations
                ],
            },
        }


class WikipediaTestCase(JwtAPITestCase):
    class QueryWikipediaMockResponse:
        status_code = status.HTTP_200_OK

        def __init__(self, limit: int, offset: int):
            self.results = [
                {
                    "id": WikipediaTestCase.get_random_wikipedia_qid(),
                    "label": faker.word(),
                    "description": faker.sentence(),
                }
                for _ in range(limit)
            ]
            self.search_continue = offset + limit

        def json(self):
            return {"search": self.results, "search-continue": self.search_continue}

    class GetWikipediaTagMocked:
        status_code = status.HTTP_200_OK

        def __init__(self, wikipedia_qid: str, en: bool, fr: bool):
            self.wikipedia_qid = wikipedia_qid
            self.languages = [
                language for language, value in {"en": en, "fr": fr}.items() if value
            ]

        def json(self):
            return {
                "entities": {
                    self.wikipedia_qid: {
                        "labels": {
                            language: {
                                "language": language,
                                "value": f"title_{language}_{self.wikipedia_qid}",
                            }
                            for language in self.languages
                        },
                        "descriptions": {
                            language: {
                                "language": language,
                                "value": f"description_{language}_{self.wikipedia_qid}",
                            }
                            for language in self.languages
                        },
                    }
                }
            }

    @classmethod
    def get_random_wikipedia_qid(cls):
        return f"Q{random.randint(100000, 999999)}"  # nosec

    @classmethod
    def get_wikipedia_tag_mocked_return(
        cls,
        wikipedia_qid: str,
        en: bool = True,
        fr: bool = True,
    ):
        return cls.GetWikipediaTagMocked(wikipedia_qid, en, fr)

    @classmethod
    def search_wikipedia_tag_mocked_return(cls, limit: int, offset: int):
        return cls.QueryWikipediaMockResponse(limit, offset)

    @classmethod
    def get_wikipedia_tag_mocked_side_effect(cls, wikipedia_qid: str):
        return cls.get_wikipedia_tag_mocked_return(wikipedia_qid)

    @classmethod
    def search_wikipedia_tag_mocked_side_effect(
        cls, query: str, language: str = "en", limit: int = 10, offset: int = 0
    ):
        return cls.search_wikipedia_tag_mocked_return(limit, offset)