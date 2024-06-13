from projects.settings.local import *  # noqa: F401, F403

ENVIRONMENT = "fullstack"

FRONTEND_URL = "https://localhost:8080"
PUBLIC_URL = "http://localhost:8000"

AWS_S3_ENDPOINT_URL = (
    # For reading images from local Minio
    # "http://minio:9000"  # noqa: E800
    # For posting images to local Minio
    "http://localhost:9000"  # noqa: E800
)

GOOGLE_EMAIL_PREFIX = "fullstack"
