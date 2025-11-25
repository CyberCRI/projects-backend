"""
WSGI config for projects core.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projects.settings.base")

application = get_wsgi_application()


from django.conf import settings  # noqa: E402

from services.crisalid.crisalid_bus import logger, start_thread  # noqa: E402

if settings.ENABLE_CRISALID_BUS:
    start_thread()
else:
    logger.info("CrisalidBus is not enabled")
