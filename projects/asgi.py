"""
ASGI config for projects projects.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projects.settings.base")

application = get_asgi_application()


from django.conf import settings  # noqa: E402

from services.crisalid.crisalid_bus import logger, start_thread  # noqa: E402

if settings.ENABLE_CRISALID_BUS:
    start_thread()
else:
    logger.info("CrisalidBus is not enabled")
