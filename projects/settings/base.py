"""
Django settings for projects core.

Generated by 'django-admin startproject' using Django 3.2.5.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""
import multiprocessing
import os
import re
from pathlib import Path
from socket import gethostbyname_ex, gethostname

from celery.schedules import crontab
from corsheaders.defaults import default_headers
from django.db.models import options
from django.utils.translation import gettext_lazy as _
from single_source import get_version

try:
    import debug_toolbar  # noqa: F401

    DEBUG_TOOLBAR_INSTALLED = True
except ImportError:
    DEBUG_TOOLBAR_INSTALLED = False

# Allow to run tests in parallel
multiprocessing.set_start_method("fork")

# Build paths inside the core like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
APPS_DIR = BASE_DIR / "apps"

__version__ = get_version(__name__, BASE_DIR)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "SECRET_KEY", "django-insecure-avpvgpdtjjm28+*z#$(t0l70u*qv7cqz4e8)r2j99hxxi@p!6$"
)  # noqa: S105

_BEHIND_HTTPS_PROXY = os.getenv("BEHIND_HTTPS_PROXY", "False") == "True"
CSRF_COOKIE_SECURE = _BEHIND_HTTPS_PROXY
SESSION_COOKIE_SECURE = _BEHIND_HTTPS_PROXY
SECURE_HSTS_PRELOAD = _BEHIND_HTTPS_PROXY
SECURE_HSTS_SECONDS = 31536000
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Silence unrelevant system checks
SILENCED_SYSTEM_CHECKS = [
    "security.W003",  # No CSRF middleware
    "security.W005",  # There's no need to set SECURE_HSTS_INCLUDE_SUBDOMAINS
    "security.W008",  # Nginx is handling the redirection to https, no need to enforce it here
    "drf_spectacular.W001",  # No need to prevent the deployment for that
    "drf_spectacular.W002",  # No need to prevent the deployment for that
]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv("DEBUG", False) == "True"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("LOG_LEVEL", "INFO"),
    },
    "loggers": {
        "django.db.backends": {
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "handlers": ["console"],
        },
        "azure": {
            "level": "ERROR",
            "handlers": ["console"],
        },
    },
}

# Urls allowed to serve this backend application
# https://docs.djangoproject.com/en/4.2/ref/settings/#allowed-hosts
# Trick to get current ip for kubernetes probes
# https://stackoverflow.com/questions/37031749/django-allowed-hosts-ips-range
ALLOWED_HOSTS = [
    *os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(","),
    gethostname(),
] + list(set(gethostbyname_ex(gethostname())[2]))

# Application definition
INSTALLED_APPS = [
    # built-in
    "django.contrib.admin",
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.messages",
    "django.contrib.postgres",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    # external
    "algoliasearch_django",
    "corsheaders",
    "django_cleanup.apps.CleanupConfig",
    "django_extensions",
    "django_filters",
    "drf_spectacular",
    "mjml",
    "modeltranslation",
    "rest_framework",
    "simple_history",
    "drf_recaptcha",
    "stdimage",
    "rest_framework_simplejwt",
    "guardian",
    "django_prometheus",
    # internal
    "apps.accounts",
    "apps.analytics",
    "apps.announcements",
    "apps.commons",
    "apps.feedbacks",
    "apps.files",
    "apps.goals",
    "apps.healthcheck",
    "apps.misc",
    "apps.notifications",
    "apps.organizations",
    "apps.projects",
    "apps.invitations",
    "apps.search",
    "apps.deploys",
    "apps.emailing",
    # services
    "services.keycloak",
    "services.mixpanel",
    "services.google",
]

if DEBUG and DEBUG_TOOLBAR_INSTALLED:
    # Insert 'debug_toolbar' right before internal apps
    for i, v in enumerate(INSTALLED_APPS):
        if v.startswith("apps."):
            INSTALLED_APPS.insert(i - 1, "debug_toolbar")
            break

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # i18n, see https://www.django-rest-framework.org/topics/internationalization/
    "django.middleware.locale.LocaleMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "apps.accounts.middlewares.CookieTokenMiddleware",
    "projects.middlewares.PerRequestClearMiddleware",
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

if DEBUG and DEBUG_TOOLBAR_INSTALLED:
    # Insert dubug toolbar middleware after whitenoise middleware
    MIDDLEWARE.insert(2, "debug_toolbar.middleware.DebugToolbarMiddleware")

# https://pypi.org/project/django-cors-headers/#cors-allowed-origins-sequence-str
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?:\/\/localhost(:[0-9]+)?",  # Is this really needed ?
    r"^https?:\/\/127.0.0.1(:[0-9]+)?",  # Is this really needed ?
]
cors_allowed_domains = os.getenv("CORS_ALLOWED_DOMAINS")
if cors_allowed_domains:
    cors_allowed_domains_regex = (
        r"^.*\.?(" + re.escape(cors_allowed_domains).replace(",", "|") + r")$"
    )
    CORS_ALLOWED_ORIGIN_REGEXES.append(cors_allowed_domains_regex)

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = list(default_headers) + [
    "cache-control",  # Used by People frontend
]
ROOT_URLCONF = "projects.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            BASE_DIR / "templates",
            BASE_DIR / "apps/accounts/templates",
            BASE_DIR / "apps/emailing/templates",
            BASE_DIR / "apps/invitations/templates",
            BASE_DIR / "services/keycloak/templates",
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "projects.wsgi.application"

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.getenv("POSTGRES_DB", "postgres"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "password"),
        "HOST": os.getenv("POSTGRES_HOST", "postgres"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = "en-us"

LANGUAGES = [
    ("en", _("English")),
    ("fr", _("French")),
]

LOCALE_PATHS = (BASE_DIR / "locale",)

REQUIRED_LANGUAGES = [code for code, _ in LANGUAGES]

TIME_ZONE = "UTC"

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# DJANGO REST FRAMEWORK
# https://www.django-rest-framework.org/

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.accounts.authentication.ProjectJWTAuthentication",
    ),
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.commons.pagination.PageInfoLimitOffsetPagination",
    "PAGE_SIZE": 100,
    "DEFAULT_SCHEMA_CLASS": "apps.commons.swagger.CustomAutoSchema",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "UNAUTHENTICATED_USER": "apps.accounts.models.AnonymousUser",
}

# Authentication
# https://mozilla-django-oidc.readthedocs.io/en/stable/
AUTHENTICATION_BACKENDS = [
    "apps.accounts.authentication.AdminAuthentication",
    "guardian.backends.ObjectPermissionBackend",
]
AUTH_USER_MODEL = "accounts.ProjectUser"

# Django Guardian
ANONYMOUS_USER_NAME = None
GUARDIAN_RAISE_403 = True


KEYCLOAK_ROOT_GROUP = os.getenv("KEYCLOAK_ROOT_GROUP", "projects")
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", "http://keycloak:8080/")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "lp")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "projects-backend-local")
KEYCLOAK_CLIENT_SECRET = os.getenv(
    "KEYCLOAK_CLIENT_SECRET", "03nfDv4dHCc97w7E4uvtdyiW4xVD6GYw"
)
KEYCLOAK_PUBLIC_KEY = os.getenv(
    "KEYCLOAK_PUBLIC_KEY",
    "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA3mtBw0bHM9fMD5dDtuOoiSrdIgsS9sugCXGPu2TTiXreRKB/EhOg/EkLf4DsOWhVwoMHc+q0Cq08mBLDQwdOB4NE1gEEHp7k3Osq/kQH5ClmZ8jaQ0CW7Rwmak21tDLjwhFQEEJJ6V4v3o4+bSBrPfNPzrynShVtzF7G2OpZlJApAebrPyzm7EXoecLBI0La0qw1tYnfCKt5W8sXivV9+4eFdJ8StH3QSaDdYjbPUR+WblTwDh5YO46uynm1KtPYuKYLbvsf1xi68v66S0ocSOXTBAmhBWv2QEpl7s/7MzV972WQR/9d4AbmMUtI4AMEIIEmeOis5g/mgMdQ0lVpPQIDAQAB",
)
KEYCLOAK_PUBLIC_KEY = (
    f"-----BEGIN PUBLIC KEY-----\n{KEYCLOAK_PUBLIC_KEY}\n-----END PUBLIC KEY-----"
)

# DRF Simple JWT
# From https://django-rest-framework-simplejwt.readthedocs.io/en/latest/settings.html
SIMPLE_JWT = {
    "AUTH_HEADER_TYPES": ("Bearer", "JWT", "Invite", "Service"),
    "USER_ID_FIELD": "keycloak_account__keycloak_id",
    "USER_ID_CLAIM": "sub",
    "TOKEN_TYPE_CLAIM": "typ",
    "AUTH_TOKEN_CLASSES": ("apps.accounts.authentication.BearerToken",),
    "ALGORITHM": "RS256",
    "VERIFYING_KEY": KEYCLOAK_PUBLIC_KEY,
}


# SWAGGER
# https://github.com/tfranzel/drf-spectacular
SPECTACULAR_SETTINGS = {
    "TITLE": "Learning Planet Institute Projects API",
    "VERSION": __version__,
    "CAMELIZE_NAMES": True,
    "COMPONENT_SPLIT_REQUEST": True,
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny"],
    "SCHEMA_PATH_PREFIX": "/v1",
    "SWAGGER_UI_SETTINGS": {
        "filter": True,
        "displayRequestDuration": True,
        "syntaxHighlight.activate": True,
        "syntaxHighlight.theme": "monokai",
    },
    "SWAGGER_UI_OAUTH2_CONFIG": {
        "clientId": KEYCLOAK_CLIENT_ID,
        "clientSecret": KEYCLOAK_CLIENT_SECRET,
        "realm": KEYCLOAK_REALM,
    },
}

# Storage
DEFAULT_FILE_STORAGE = os.getenv(
    "DEFAULT_FILE_STORAGE", "django.core.files.storage.FileSystemStorage"
)

AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL", None)
AZURE_ACCOUNT_KEY = os.getenv("AZURE_ACCOUNT_KEY", None)
if AWS_S3_ENDPOINT_URL is not None:
    DEFAULT_FILE_STORAGE = os.getenv(
        "DEFAULT_FILE_STORAGE", "storages.backends.s3boto3.S3Boto3Storage"
    )
elif AZURE_ACCOUNT_KEY is not None:
    DEFAULT_FILE_STORAGE = os.getenv(
        "DEFAULT_FILE_STORAGE", "storages.backends.azure_storage.AzureStorage"
    )
AWS_S3_ACCESS_KEY_ID = os.getenv("AWS_S3_ACCESS_KEY_ID", "minioadmin")
AWS_S3_SECRET_ACCESS_KEY = os.getenv("AWS_S3_SECRET_ACCESS_KEY", "minioadmin")
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "projects")
AWS_DEFAULT_ACL = None

AZURE_ACCOUNT_NAME = os.getenv("AZURE_ACCOUNT_NAME", "criparisdevlabprojects")
AZURE_CONTAINER = os.getenv("AZURE_CONTAINER", "projects")
AZURE_URL_EXPIRATION_SECS = int(os.getenv("AZURE_URL_EXPIRATION_SECS", "3600"))
AZURE_CUSTOM_DOMAIN = os.getenv("AZURE_CUSTOM_DOMAIN")
AZURE_CACHE_CONTROL = f"private,max-age={AZURE_URL_EXPIRATION_SECS},must-revalidate"

##############
#   CELERY   #
##############

CELERY_WORKER_SEND_TASK_EVENTS = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True
CELERY_BEAT_SCHEDULE = {
    "delete-orphan-images": {
        "task": "apps.files.tasks.delete_orphan_images",
        "schedule": crontab(minute=0, hour=2),
    },
    "remove-old-project-24hours": {
        "task": "apps.projects.tasks.remove_old_projects",
        "schedule": crontab(minute=0, hour=0),
    },
    "send_notifications_reminder": {
        "task": "apps.notifications.tasks.send_notifications_reminder",
        "schedule": crontab(minute=0, hour=8),
    },
    "send_invitations_reminder": {
        "task": "apps.invitations.tasks.send_invitations_reminder",
        "schedule": crontab(minute=0, hour=7),
    },
    "get_new_mixpanel_events": {
        "task": "services.mixpanel.tasks.get_new_mixpanel_events",
        "schedule": crontab(minute="*/2", hour="*"),
    },
    "retry_google_failed_tasks": {
        "task": "services.google.tasks.retry_failed_tasks",
        "schedule": crontab(minute="*/10", hour="*"),
    },
}

# Cache settings
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("CACHE_REDIS_URL", "redis://redis:6379/1"),
    },
}
ENABLE_CACHE = True
CACHE_DEFAULT_TTL = int(os.getenv("CACHE_DEFAULT_TTL", 30))
CACHE_ORGANIZATIONS_LIST_TTL = 60 * int(
    os.getenv("CACHE_ORGANIZATIONS_LIST_TTL", CACHE_DEFAULT_TTL)
)
CACHE_CATEGORIES_LIST_TTL = 60 * int(
    os.getenv("CACHE_CATEGORIES_LIST_TTL", CACHE_DEFAULT_TTL)
)
CACHE_ANNOUNCEMENTS_LIST_TTL = 60 * int(
    os.getenv("CACHE_ANNOUNCEMENTS_LIST_TTL", CACHE_DEFAULT_TTL)
)
CACHE_LOCATIONS_LIST_TTL = 60 * int(
    os.getenv("CACHE_LOCATIONS_LIST_TTL", CACHE_DEFAULT_TTL)
)
CACHE_PROJECT_VIEWS = 86400  # 1 day

#############
#   Emails  #
#############

EMAIL_HOST = os.getenv("EMAIL_HOST", "mailhog")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "1025"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "projects@mg.lp-i.dev")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_SSL = os.getenv("EMAIL_USE_SSL", False)

EMAIL_REPORT_RECIPIENTS = ["projects.platform@learningplanetinstitute.org"]

# Time (in seconds) after which an image is considered an orphan if it was not assigned to
# any model.
IMAGE_ORPHAN_THRESHOLD_SECONDS = 86400  # 1 day

# URL for wikipedia gateway service
WIKIPEDIA_GATEWAY_URL = os.getenv(
    "WIKIPEDIA_GATEWAY_URL", "https://wikipedia-gateway.k8s.lp-i.dev"
)

# MJML
MJML_BACKEND_MODE = "httpserver"
MJML_HTTPSERVERS = [
    {
        "URL": os.getenv("MJML_HTTPSERVER_URL", "http://mjml:15500/v1/render"),
    },
]

# drf-recaptcha settings => https://pypi.org/project/drf-recaptcha/
DRF_RECAPTCHA_SECRET_KEY = os.getenv("RECAPTCHA_SECRET_KEY", None)
DRF_RECAPTCHA_TESTING = DRF_RECAPTCHA_SECRET_KEY is None

# URL for Projects API
PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:8000")

# to allow debug toolbar
INTERNAL_IPS = [
    # ...
    "127.0.0.1",
    # ...
]
if DEBUG:
    import socket  # only if you haven't already imported this

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS = [ip[: ip.rfind(".")] + ".1" for ip in ips] + [
        "127.0.0.1",
        "10.0.2.2",
    ]

# Python requests module default timeout
REQUESTS_DEFAULT_TIMEOUT = 10

# Hard Delete Project Time in days
DELETED_PROJECT_RETENTION_DAYS = 0

# Authentication cookie name
JWT_ACCESS_TOKEN_COOKIE_NAME = "jwt_access_token"  # nosec

# The maximum number of parameters that may be received via GET or POST
DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

# Minimum similarity threshold for trigram similarity search
PG_TRGM_DEFAULT_SIMILARITY_THRESHOLD = 0.33

# Django guardian custom setup
# TODO : django-guardian rework : can't remove additional_actions for now
options.DEFAULT_NAMES += ("subscopes", "write_only_subscopes", "additional_actions")

# Algolia settings
# See https://www.algolia.com/doc/framework-integration/django/setup/?client=python#setup
ALGOLIA = {
    "APPLICATION_ID": os.getenv(
        "ALGOLIA_APP_ID", "NOT_SET"
    ),  # Cannot set None by default, it fails
    "API_KEY": os.getenv(
        "ALGOLIA_KEY", "NOT_SET"
    ),  # Cannot set None by default, it fails
    "INDEX_PREFIX": os.getenv("ALGOLIA_PREFIX", ""),
    "INDEX_SUFFIX": os.getenv("ALGOLIA_SUFFIX", ""),
}

##############
#   PEOPLE   #
##############

PEOPLE_API_ROOT = "https://api.people.cri-paris.org"
PROJECTS_PEOPLE_TOKEN = os.getenv("PROJECTS_PEOPLE_TOKEN")

##############
#   RECSYS   #
##############

RECSYS_API_URL = "https://recsys-api.k8s.lp-i.xyz"

#####################
#   Static files    #
#####################

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"
STATICFILES_DIRS = [
    BASE_DIR / "assets",
]
# Add compression and caching support
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


##############
#  MIXPANEL  #
##############

MIXPANEL_PROJECT_ID = "2511917"
MIXPANEL_API_SECRET = os.getenv("MIXPANEL_API_SECRET", "NOT SET")


##############
#   GOOGLE   #
##############

GOOGLE_SYNCED_ORGANIZATION = "CRI"
GOOGLE_CREDENTIALS = {
    "type": "service_account",
    "project_id": "lpi-accounts-391112",
    "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID", ""),
    "private_key": os.getenv("GOOGLE_PRIVATE_KEY", ""),
    "client_email": "lpi-accounts@lpi-accounts-391112.iam.gserviceaccount.com",
    "client_id": "111578588399348351692",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/lpi-accounts%40lpi-accounts-391112.iam.gserviceaccount.com",
}
GOOGLE_CUSTOMER_ID = "C03m9cf4b"
GOOGLE_SERVICE_NAME = "admin"
GOOGLE_SERVICE_VERSION = "directory_v1"
GOOGLE_SERVICE_ACCOUNT_EMAIL = "lpi.accounts@gworkspacetest.cri-paris.org"
GOOGLE_EMAIL_PREFIX = ""
GOOGLE_EMAIL_DOMAIN = "gworkspacetest.cri-paris.org"
GOOGLE_EMAIL_ALIAS_DOMAIN = "gworkspacetest.learningplanetinstitute.org"
