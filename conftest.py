import pytest


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Create the global permission groups once per test session.

    `get_superadmins_group()` assigns every permission to the group the first
    time it is called (and it is called on every authenticated request).
    Without this, each test recreates it inside its own transaction, which is
    then rolled back.
    """
    from apps.accounts.utils import get_default_group, get_superadmins_group

    with django_db_blocker.unblock():
        get_superadmins_group()
        get_default_group()
