from django.core.exceptions import ValidationError


def file_size(file, max_size: int = 10):
    """
    Raises an error in file is too large. max_size is 10MB by default but can be set for specific cases.
    """
    limit = max_size * 1024 * 1024
    if file.size > limit:
        raise ValidationError(
            {"error": f"File too large. Size should not exceed {max_size} MB."}
        )
