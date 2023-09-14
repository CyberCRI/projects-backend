from apps.accounts.models import PeopleGroup, ProjectUser


class LPIGoogleAccount(ProjectUser):
    class Meta:
        proxy = True


class LPIGoogleGroup(PeopleGroup):
    class Meta:
        proxy = True
