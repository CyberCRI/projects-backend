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
            "alternativeLabel": {
                # Test when alternative label is provided in only one language
                "en": [
                    f"{title_en} alternative 1",
                    f"{title_en} alternative 2",
                ]
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
                "fr": title_fr,
                "en": title_en,
            },
            "alternativeLabel": {
                # Test when alternative label is provided in only one language
                "en": [
                    f"{title_en} alternative 1",
                    f"{title_en} alternative 2",
                ]
            },
            "description": {
                "fr": {"literal": description_fr, "mimetype": "plain/text"},
                "en": {"literal": description_en, "mimetype": "plain/text"},
            },
            "alternativeTerms": {
                "fr": [
                    {"roles": ["male"], "label": f"{title_fr} male"},
                    {"roles": ["female"], "label": f"{title_fr} female"},
                ],
                "en": [
                    {"roles": ["male"], "label": f"{title_en} male"},
                    {"roles": ["female"], "label": f"{title_en} female"},
                ],
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

        def __init__(self, limit: int, offset: int, wikipedia_qids: List[str] = None):
            self.results = [
                {
                    "id": WikipediaTestCase.get_random_wikipedia_qid(),
                    "label": faker.word(),
                    "description": faker.sentence(),
                }
                for _ in range(limit)
            ]
            self.search_continue = offset + limit
            if wikipedia_qids is not None:
                if not isinstance(wikipedia_qids, list) or not all(
                    isinstance(wikipedia_qid, str) for wikipedia_qid in wikipedia_qids
                ):
                    raise ValueError("wikipedia_qids must be a list of strings")
                self.results = [
                    {
                        "id": wikipedia_qid,
                        "label": f"title_{wikipedia_qid}",
                        "description": f"description_{wikipedia_qid}",
                    }
                    for wikipedia_qid in wikipedia_qids[offset : offset + limit]
                ] + self.results
                self.results = self.results[:limit]

        def json(self):
            return {"search": self.results, "search-continue": self.search_continue}

    class GetWikipediaTagsMocked:
        status_code = status.HTTP_200_OK

        def __init__(self, wikipedia_qids: List[str], en: bool, fr: bool):
            self.wikipedia_qids = wikipedia_qids
            self.languages = [
                language for language, value in {"en": en, "fr": fr}.items() if value
            ]
            # add a language that should be ignored except for fallback
            self.languages.append("xx")

        def json(self):
            return {
                "entities": {
                    wikipedia_qid: {
                        "labels": {
                            language: {
                                "language": language,
                                "value": f"title_{language}_{wikipedia_qid}",
                            }
                            for language in self.languages
                        },
                        "descriptions": {
                            language: {
                                "language": language,
                                "value": f"description_{language}_{wikipedia_qid}",
                            }
                            for language in self.languages
                        },
                    }
                    for wikipedia_qid in self.wikipedia_qids
                }
            }

    class GetExistingWikipediaTagsMocked:
        status_code = status.HTTP_200_OK

        def __init__(self, tags: List[Tag], en: bool, fr: bool):
            self.tags = tags
            self.languages = [
                language for language, value in {"en": en, "fr": fr}.items() if value
            ]
            # add a language that should be ignored except for fallback
            self.languages.append("xx")

        def json(self):
            """
            Return a mocked response for the Wikipedia API.
            Add a " _" at the end of the values to allow testing of the update mechanism
            """
            return {
                "entities": {
                    tag.external_id: {
                        "labels": {
                            language: {
                                "language": language,
                                "value": getattr(tag, f"title_{language}", "") + " _",
                            }
                            for language in self.languages
                        },
                        "descriptions": {
                            language: {
                                "language": language,
                                "value": getattr(tag, f"description_{language}", "")
                                + " _",
                            }
                            for language in self.languages
                        },
                    }
                    for tag in self.tags
                }
            }

    @classmethod
    def get_random_wikipedia_qid(cls):
        return f"Q{random.randint(100000, 999999)}"  # nosec

    @classmethod
    def get_wikipedia_tags_mocked_return(
        cls,
        wikipedia_qids: List[str],
        en: bool = True,
        fr: bool = True,
    ):
        return cls.GetWikipediaTagsMocked(wikipedia_qids, en, fr)

    @classmethod
    def get_existing_wikipedia_tags_mocked_return(
        cls,
        tags: List[Tag],
        en: bool = True,
        fr: bool = True,
    ):
        return cls.GetExistingWikipediaTagsMocked(tags, en, fr)

    @classmethod
    def search_wikipedia_tag_mocked_return(
        cls, limit: int, offset: int, wikipedia_qids: List[str] = None
    ):
        return cls.QueryWikipediaMockResponse(limit, offset, wikipedia_qids)

    @classmethod
    def get_wikipedia_tags_mocked_side_effect(cls, wikipedia_qids: List[str]):
        return cls.get_wikipedia_tags_mocked_return(wikipedia_qids)

    @classmethod
    def search_wikipedia_tag_mocked_side_effect(
        cls, query: str, language: str = "en", limit: int = 10, offset: int = 0
    ):
        return cls.search_wikipedia_tag_mocked_return(limit, offset)

    @classmethod
    def search_wikipedia_tag_mocked_side_effect_with_given_ids(
        cls, given_ids: List[str]
    ):
        def side_effect(
            query: str, language: str = "en", limit: int = 10, offset: int = 0
        ):
            return cls.search_wikipedia_tag_mocked_return(limit, offset, given_ids)

        return side_effect
