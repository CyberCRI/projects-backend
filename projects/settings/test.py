from projects.settings.base import *  # noqa: F401, F403

# force remove
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "debug_toolbar"]  # noqa: F405
MIDDLEWARE = [
    mid
    for mid in MIDDLEWARE  # noqa: F405
    if mid != "debug_toolbar.middleware.DebugToolbarMiddleware"
]

ENVIRONMENT = "test"
FRONTEND_URL = "http://frontend.com"


##############
#  STORAGES  #
##############

STORAGES = {
    "default": {"BACKEND": "inmemorystorage.InMemoryStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


##############
#   CACHE    #
##############

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    },
}
ENABLE_CACHE = False


##############
#    AUTH    #
##############

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

SIMPLE_JWT["ALGORITHM"] = "HS256"  # noqa: F405


##############
#   EMAILS   #
##############

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

##############
#   GOOGLE   #
##############

GOOGLE_SYNCED_ORGANIZATION = "TEST_GOOGLE_SYNC"
GOOGLE_EMAIL_PREFIX = "test"

TEST_RUNNER = "django_slowtests.testrunner.DiscoverSlowestTestsRunner"
NUM_SLOW_TESTS = 10


##############
# OpenSearch #
##############

OPENSEARCH_DSL_AUTO_REFRESH = False
OPENSEARCH_DSL_AUTOSYNC = False
OPENSEARCH_DSL_PARALLEL = True
OPENSEARCH_DSL_SIGNAL_PROCESSOR = (
    "django_opensearch_dsl.signals.RealTimeSignalProcessor"
)
OPENSEARCH_INDEX_PREFIX = "proj-test"

ENABLE_CRISALID_BUS = False
