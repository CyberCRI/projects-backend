from drf_spectacular.openapi import AutoSchema


class CustomAutoSchema(AutoSchema):
    """Custom `AutoSchema` allowing `summary` to default to `description`."""

    def get_operation(self, *args, **kwargs):
        operation = super().get_operation(*args, **kwargs)
        if "summary" not in operation:
            title = operation.get("description")
            if title is not None and len(title) > 150:
                title = title[:148] + "..."
            operation.setdefault("summary", title)

        return operation


class swagger_fake_value:  # noqa : N801
    """Decorator which return the given value instead of calling the function
    it decorates.

    `drf-spectacular` calls some methods of viewsets and serializers to create
    schema of the different endpoints. These methods may be called without any
    active `User`, which can cause some issue (for instance when checking for
    permissions).

    This decorator allows to bypass the function it decorated altogether,
    returning instead the value given to the constructor.
    """

    def __init__(self, value):
        self.value = value

    def __call__(self, f):
        def wrapped(self_, *args, **kwargs):
            if getattr(self_, "swagger_fake_view", False):
                return self.value
            return f(self_, *args, **kwargs)

        return wrapped
