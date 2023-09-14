from django.utils.functional import SimpleLazyObject


class CustomLazyObject(SimpleLazyObject):
    """Equivalent to Django's `SimpleLazyObject`, but call to `isinstance()` and
    such does not evaluate the function.

    This is useful for instance to avoid test discovery triggering the
    evaluation of the object."""

    @property
    def __class__(self):
        return type(self)
