import re
from typing import List

import requests
from django.conf import settings

from apps.projects.models import Project


class RecsysService:
    @staticmethod
    def remove_html_tags(text: str) -> str:
        """Remove html tags from a string"""
        pattern = re.compile("<.*?>")
        clean_text = re.sub(pattern, " ", text)
        clean_text = re.sub("&nbsp;", " ", clean_text)
        return re.sub(" +", " ", clean_text).strip()

    @classmethod
    def get_text_query_from_project(cls, project: Project) -> str:
        """
        Create a text query from the project's following fields:
            - title
            - description
            - purpose
            - wikipedia tags (in the projects language)
        """
        return "\n".join(
            [
                project.title,
                project.purpose,
                cls.remove_html_tags(project.description),
                ", ".join(
                    [
                        getattr(w, f"name_{project.language}")
                        if getattr(w, f"name_{project.language}")
                        else w.name
                        for w in project.wikipedia_tags.all()
                    ]
                ),
            ]
        )

    @classmethod
    def get_similar_projects(
        cls, project: Project, threshold: int, languages: List[str]
    ):
        """
        Get similar projects from recsys

        Arguments
        ---------
        project: Project
            Project for which you want similar resources
        threshlod: Integer
            Number of results
        langugaes: List of strings
            Languages filter for the results (en and/or fr)
        """
        payload = {
            "query": cls.get_text_query_from_project(project),
            "results_threshold": threshold,
            "language": languages,
            "corpus": ["Project"],
        }
        response = requests.post(
            f"{settings.RECSYS_API_URL}/api/v1/resource/search/", data=payload
        )
        return {p["url"].split("/")[-1]: p["similarity"] for p in response.json()}
