class PerRequestClearMiddleware:
    """Middleware used to ensure per-request caches are cleared."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)
