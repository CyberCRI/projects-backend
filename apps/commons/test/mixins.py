import os
from unittest import skipUnless


def skipUnlessAlgolia(decorated):  # noqa : N802
    """Skip decorated tests if ennvar `TEST_ALGOLIA` has not been set to 1."""
    check = bool(int(os.getenv("TEST_ALGOLIA", 0)))
    msg = "Algolia test skipped, use envvar 'TEST_ALGOLIA=1' to test"
    return skipUnless(check, msg)(decorated)


def skipUnlessGoogle(decorated):  # noqa : N802
    """Skip decorated tests if ennvar `TEST_ALGOLIA` has not been set to 1."""
    check = bool(int(os.getenv("TEST_GOOGLE", 0)))
    msg = "Google test skipped, use envvar 'TEST_GOOGLE=1' to test"
    return skipUnless(check, msg)(decorated)
