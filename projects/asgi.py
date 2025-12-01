"""
ASGI config for projects projects.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import asyncio
import logging
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "projects.settings.base")

application = get_asgi_application()


from django.conf import settings  # noqa: E402

if settings.ENABLE_CRISALID_BUS:
    # we are in async context, so wee need to wrap
    # the sync function "intitial_tart_crisalid" to a corotine
    # and put it in current event loop
    from asgiref.sync import sync_to_async

    from services.crisalid.bus.runner import initial_start_crisalidbus  # noqa: E402

    loop = asyncio.get_event_loop()
    loop.create_task(sync_to_async(initial_start_crisalidbus)())

else:
    logging.info("CrisalidBus is not enabled")
