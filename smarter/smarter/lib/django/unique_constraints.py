"""
The check that a migration runs before it adds a unique constraint to a table that already has rows.

A unique constraint that replaces a ``unique_together`` on the same columns can't fail on a healthy
database: the old unique index already refused duplicates. MariaDB commits each schema change at once,
though, so a database whose earlier migration failed halfway may lack that index, and may hold
duplicates. ``ALTER TABLE ... ADD CONSTRAINT`` would then fail with an ``IntegrityError`` that names
neither the rows nor what to do about them.

:func:`refuse_duplicates` returns a ``RunPython`` operation that a migration lists before its
``AddConstraint`` operations. It changes nothing. When the table holds rows that the constraint would
refuse, it stops the migration before any schema change, and its error names the model, the columns
and the ids of the duplicate rows, never their values, which can be names or email addresses.
"""

from collections.abc import Callable, Sequence

from django.db import migrations
from django.db.models import Count

MigrationFunction = Callable[[object, object], None]
"""The signature of a ``RunPython`` function: ``(apps, schema_editor)``."""

MAX_GROUPS_IN_ERROR = 10
"""How many groups of duplicate rows the error lists.

It gives the total too.
"""


class SmarterDuplicateRowsError(Exception):
    """A table holds rows that a unique constraint, about to be added, would refuse."""


def duplicate_row_ids(model, fields: Sequence[str]) -> list[list[int]]:
    """
    Return the ids of each group of rows that share the same values of ``fields``.

    Rows with a NULL in any of ``fields`` aren't duplicates: MariaDB's unique indexes allow
    any number of them.

    :param model: The model, usually the historical one from ``apps.get_model()``.
    :param fields: The names of the fields that the constraint makes unique together.
    :returns: One sorted list of ids per group of two or more rows, or an empty list.
    """
    rows = model.objects.all()
    for field in fields:
        null_filter = {f"{field}__isnull": False}
        rows = rows.filter(**null_filter)
    grouped = rows.values(*fields).annotate(row_count=Count("pk"))
    duplicate_groups = grouped.filter(row_count__gt=1)

    retval = []
    for group in duplicate_groups:
        same_values = {}
        for field in fields:
            same_values[field] = group[field]
        ids = model.objects.filter(**same_values).order_by("pk").values_list("pk", flat=True)
        retval.append(list(ids))
    return retval


def _forward(app_label: str, model_name: str, fields: tuple[str, ...]) -> MigrationFunction:
    # pylint: disable=W0613
    def forward(apps, schema_editor) -> None:
        model = apps.get_model(app_label, model_name)
        groups = duplicate_row_ids(model, fields)
        if not groups:
            return
        shown_groups = groups[:MAX_GROUPS_IN_ERROR]
        field_names = ", ".join(fields)
        message = (
            f"{app_label}.{model_name} has {len(groups)} group(s) of rows with the same ({field_names}), "
            f"which the new unique constraint refuses. The ids of each group: {shown_groups}. "
            "Delete or rename the extra rows, then run the migration again."
        )
        raise SmarterDuplicateRowsError(message)

    return forward


def refuse_duplicates(app_label: str, model_name: str, fields: Sequence[str]) -> migrations.RunPython:
    """
    Return the ``RunPython`` operation that stops a migration when a table holds duplicate rows.

    List it before the migration's ``AddConstraint`` operations, one per constraint, so that it
    runs before any schema change.

    :param app_label: The model's app label, e.g. ``"secret"``.
    :param model_name: The model's name, e.g. ``"secret"``.
    :param fields: The names of the fields that the constraint makes unique together.
    :returns: The operation. Its reverse does nothing.
    :raises SmarterDuplicateRowsError: When the migration runs, if the table holds duplicates.
    """
    forward = _forward(app_label, model_name, tuple(fields))
    operation = migrations.RunPython(forward, migrations.RunPython.noop)
    return operation
