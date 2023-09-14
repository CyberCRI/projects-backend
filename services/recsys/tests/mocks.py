import random
from typing import List

from apps.projects.models import Project


class RecsysMockResponse:
    def __init__(self, projects: List[Project], status_code: int = 200):
        self.status_code = status_code
        self.dict = [
            {
                "corpus": "Project",
                "similarity": round(random.uniform(0.0, 10.0), 3),  # nosec
                "id": random.randint(0, 1000),
                "faiss_id": random.randint(0, 1000),
                "title": project.title,
                "description": project.purpose,
                "url": f"https://projects.directory/projects/{project.id}",
                "lang": project.language,
            }
            for project in projects
        ]

    def json(self):
        return self.dict
