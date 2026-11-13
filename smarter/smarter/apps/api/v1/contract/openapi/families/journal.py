"""The Smarter Journal's REST reads, under ``/api/v1/journal/``: a record of every request to the cli api."""

from smarter.apps.api.v1.contract.models import (
    OpenApiParameter,
    OpenApiPathItem,
    OpenApiSchema,
)
from smarter.apps.api.v1.contract.openapi.builders import ApiFamily, query, rest_read
from smarter.lib.journal.api.v1.views import SORT_FIELDS as JOURNAL_SORT_FIELDS
from smarter.lib.journal.const import namespace
from smarter.lib.journal.contract.const import JOURNAL_KEY_PATTERN
from smarter.lib.journal.contract.models import SAMJournalApiEntry, SAMJournalApiPage

JOURNAL = ApiFamily(
    name=namespace,
    resource=f"{namespace} entry",
    urlconf="smarter.lib.journal.api.v1.urls",
    description="The Smarter Journal: a record of every request to the cli api. For superusers.",
    tag_name=namespace,
)
"""The Smarter Journal's family, whose tag, and so its routes, are its name, in the singular."""


def journal_paths() -> dict[str, OpenApiPathItem]:
    """
    The Smarter Journal's REST reads, relative to the server's ``/api/v1``.

    Only superusers may call them.

    :returns: The paths, e.g. ``{"/journal/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    family = JOURNAL
    # Each sortable column, ascending (``createdAt``) and descending (``-createdAt``).
    # A list[str] is not a JsonValue, whose lists are invariant list[JsonValue].
    ordering_values: list[OpenApiSchema] = []
    for column in JOURNAL_SORT_FIELDS:
        ordering_values.append(f"{column}")
        ordering_values.append(f"-{column}")
    return {
        family.path(): OpenApiPathItem(
            get=rest_read(
                family.operation_id("list"),
                f"List {family.plural}",
                f"One page of the {family.name}'s entries, newest first unless sorted, without their request and "
                "response documents.",
                family.tag,
                SAMJournalApiPage.__name__,
                many=False,
                parameters=[
                    query("page", "The page, from 1.", {"type": "integer", "default": 1}),
                    query("page_size", "The entries of a page, at most 100.", {"type": "integer", "default": 25}),
                    query("search", "Text that an entry's key, thing or command contains.", {"type": "string"}),
                    query(
                        "ordering",
                        "The column to sort by, e.g. createdAt, or -createdAt to sort it in descending order.",
                        {
                            "type": "string",
                            "enum": ordering_values,
                        },
                    ),
                ],
            )
        ),
        family.path("{key}/"): OpenApiPathItem(
            get=rest_read(
                family.operation_id("retrieve"),
                family.a_capitalized,
                f"{family.a_capitalized}, by its key, with its request and response documents. The request "
                "document holds the caller's headers, including its api key.",
                family.tag,
                SAMJournalApiEntry.__name__,
                many=False,
                parameters=[
                    OpenApiParameter(
                        name="key",
                        in_="path",
                        required=True,
                        description="The entry's key, 64 hexadecimal characters.",
                        schema_={"type": "string", "pattern": JOURNAL_KEY_PATTERN},
                    )
                ],
            )
        ),
    }


__all__ = ["JOURNAL", "journal_paths"]
