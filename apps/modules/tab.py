from typing import Any

from django.db.models import QuerySet

from apps.modules.base import AbstractModules, register_module
from apps.projects.models import Project, ProjectTab


@register_module(ProjectTab)
class TabModules(AbstractModules):
    instance: ProjectTab

    def items(self) -> QuerySet[Any]:
        if self.instance.type in ProjectTab.PROJECT_TYPE_BRIDGE:
            method = getattr(
                self.instance.project.modules_by_user(self.user, self.organization),
                self.instance.type,
                None,
            )
            if method is None:
                return Project.objects.filter(pk=self.instance.project.pk)
            return method()
        return self.instance.items.all()
