from django.db.models import QuerySet

from apps.modules.base import AbstractModules, register_module
from apps.projects.models import ProjectTab, ProjectTabItem


@register_module(ProjectTab)
class TabModules(AbstractModules):
    instance: ProjectTab

    def items(self) -> QuerySet[ProjectTabItem]:
        return self.instance.items.all()
