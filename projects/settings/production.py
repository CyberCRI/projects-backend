import os

from projects.settings.base import *  # noqa: F401, F403

ENVIRONMENT = "production"

FRONTEND_URL = "https://projects.directory"
PUBLIC_URL = "https://api.projects.lp-i.org"


##############
#   GOOGLE   #
##############

GOOGLE_SYNCED_ORGANIZATION = "CRI"
GOOGLE_CREDENTIALS = {
    "type": "service_account",
    "project_id": "lpi-accounts-357713",
    "private_key_id": os.getenv("GOOGLE_PRIVATE_KEY_ID", ""),
    "private_key": os.getenv("GOOGLE_PRIVATE_KEY", ""),
    "client_email": "lpi-accounts@lpi-accounts-357713.iam.gserviceaccount.com",
    "client_id": "100628103603802804718",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/lpi-accounts%40lpi-accounts-357713.iam.gserviceaccount.com",
}
GOOGLE_CUSTOMER_ID = "C04ivd6m0"
GOOGLE_SERVICE_NAME = "admin"
GOOGLE_SERVICE_VERSION = "directory_v1"
GOOGLE_SERVICE_ACCOUNT_EMAIL = "lpi.accounts@learningplanetinstitute.org"
GOOGLE_EMAIL_PREFIX = ""
GOOGLE_EMAIL_DOMAIN = "cri-paris.org"
GOOGLE_EMAIL_ALIAS_DOMAIN = "learningplanetinstitute.org"
