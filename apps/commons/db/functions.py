from django.contrib.postgres.fields import ArrayField
from django.db.models import Func, Value
from django.forms import IntegerField


class ArrayPosition(Func):
    """Allows to order the rows through a list of column's value.

    Only works with Postgresql.

    Examples
    --------
    >>> qs = Project.objects.all()
    >>> qs = qs.annotate(ordering=ArrayPosition(pk_list, F('pk'))
    >>> qs = qs.order_by('ordering')
    """

    function = "array_position"

    def __init__(
        self, items, *expressions, base_field=None, output_field=None, **extra
    ):
        if base_field is None:
            base_field = IntegerField()
        if output_field is None:
            output_field = base_field

        first_arg = Value(list(items), output_field=ArrayField(base_field))
        expressions = (first_arg,) + expressions
        super().__init__(*expressions, output_field=output_field, **extra)
