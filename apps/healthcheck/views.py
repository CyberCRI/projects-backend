from django.db import connection
from django.http import HttpResponse, HttpResponseServerError


def liveness(request):
    return HttpResponse("OK")


def readiness(request):
    try:
        connection.ensure_connection()
        if not connection.is_usable():
            return HttpResponseServerError("Database is not usable.")
        return HttpResponse("OK")
    except Exception:  # noqa: PIE786
        return HttpResponseServerError("Cannot connect to database.")
