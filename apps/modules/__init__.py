from .document import DocumentModules
from .group import PeopleGroupModules
from .organization import OrganizationModules
from .project import ProjectModules
from .researcher import ResearcherModules
from .structure import StructureModules
from .tab import TabModules
from .user import UserModules

__all__ = [
    "PeopleGroupModules",
    "ProjectModules",
    "TabModules",
    "UserModules",
    "DocumentModules",
    "ResearcherModules",
    "StructureModules",
    "OrganizationModules",
]
