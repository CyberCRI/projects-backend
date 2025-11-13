def projects(request) -> dict:
    """return backend version for admin"""
    from django.conf import settings

    context = {"settings": settings}

    return {"projects": context}
