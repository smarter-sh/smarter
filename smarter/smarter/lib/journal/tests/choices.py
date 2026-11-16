"""Test helpers that read the choices of the SAMJournal model's fields."""

from django.db import models

from smarter.lib.journal.models import SAMJournal


def field_choices(field_name: str) -> list[str]:
    """
    Return the values of a SAMJournal field's choices, e.g. ``thing`` or ``command``.

    :param field_name: The field's name.
    :returns: The values, in the field's order.
    :raises AssertionError: If the field is a relation, or has no choices.
    """
    field = SAMJournal._meta.get_field(field_name)  # pylint: disable=protected-access
    assert isinstance(field, models.Field)
    choices = field.choices
    assert choices is not None
    values = []
    for value, _ in choices:
        values.append(str(value))
    return values
