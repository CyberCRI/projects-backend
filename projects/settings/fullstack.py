from projects.settings.local import *  # noqa: F401, F403

ENVIRONMENT = "fullstack"

FRONTEND_URL = "https://localhost:8080"
PUBLIC_URL = "http://localhost:8000"

AWS_S3_ENDPOINT_URL = "http://minio:9000"  # change to "http://localhost:9000" to read from local Minio

GOOGLE_EMAIL_PREFIX = "fullstack"
