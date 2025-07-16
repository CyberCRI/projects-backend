import csv
import os
import zipfile
from typing import List

from bs4 import BeautifulSoup
from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse

from apps.projects.models import Project

from .models import Template


class ProjectTemplateExportMixin:
    """
    This extract checks the structure of the Template's description_placeholder and
    extracts the headers from the <h3> tags. It then creates a CSV file for each
    template, showing what these projects show in their description under each header.

    The CSV files are then zipped and returned as a response.
    """

    def _get_project_data(self, project: Project, headers: List[str]) -> str:
        soup = BeautifulSoup(project.description, "html.parser")
        current_header = None
        data = {header: "" for header in headers}
        for child in soup.children:
            child_text = child.get_text(strip=True)
            if child.name == "h3":
                if child_text in headers:
                    current_header = child_text
            elif current_header is not None and child_text:
                data[current_header] += child_text + " "
        return data

    def _get_template_headers(self, template: Template) -> List[str]:
        headers = []
        soup = BeautifulSoup(template.description_placeholder, "html.parser")
        for h3_tag in soup.find_all("h3"):
            headers.append(h3_tag.get_text(strip=True))
        return headers

    @admin.action(description="Export projects descriptions by template header")
    def export_data(
        self, request: HttpRequest, queryset: QuerySet[Template]
    ) -> HttpResponse:
        zip_filename = "templates_projects.zip"
        with zipfile.ZipFile(zip_filename, "w") as zipf:
            for template in queryset:
                projects = Project.objects.filter(main_category__template=template)
                headers = self._get_template_headers(template)
                lines = [["project_id", *headers]]

                for project in projects:
                    project_data = self._get_project_data(project, headers)
                    lines.append(
                        [str(project.id), *[project_data.get(h) for h in headers]]
                    )
                with open(f"{template.id}.csv", "w") as f:
                    writer = csv.writer(f, delimiter=",", quoting=csv.QUOTE_ALL)
                    writer.writerows(lines)
                zipf.write(f"{template.id}.csv", arcname=f"{template.id}.csv")
                os.remove(f"{template.id}.csv")
        with open(zip_filename, "rb") as zip_file:
            response = HttpResponse(
                zip_file.read(),
                content_type="application/zip",
                headers={
                    "Content-Disposition": f"attachment; filename={zip_filename}",
                },
            )
        os.remove(zip_filename)
        return response
