from projects.settings.base import *  # noqa: F401, F403

ENVIRONMENT = "test"

FRONTEND_URL = "http://frontend.com"

DEFAULT_FILE_STORAGE = "inmemorystorage.InMemoryStorage"

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    },
}
ENABLE_CACHE = False

SIMPLE_JWT["ALGORITHM"] = "HS256"  # noqa: F405

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

ALGOLIA["AUTO_INDEXING"] = False  # noqa: F405
ALGOLIA["INDEX_PREFIX"] = "test"  # noqa: F405

##############
#   GOOGLE   #
##############

GOOGLE_SYNCED_ORGANIZATION = "TEST_GOOGLE_SYNC"
GOOGLE_EMAIL_PREFIX = "test"

TEST_RUNNER = "django_slowtests.testrunner.DiscoverSlowestTestsRunner"
NUM_SLOW_TESTS = 10
