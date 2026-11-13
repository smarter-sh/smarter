"""The accounts' REST reads, under ``/api/v1/accounts/``, for superusers, and the user's own token usage and data exports."""

from smarter_types import SAMKinds

from smarter.apps.account.const import namespace
from smarter.apps.account.contract.models import (
    AccountApiAccountDetail,
    AccountApiContact,
    AccountApiProfile,
    AccountApiUserDetail,
)
from smarter.apps.account.data_export import (
    DataExportOverviewResponse,
    DataExportStatusResponse,
)
from smarter.apps.account.token_usage import TokenUsageSeries, TokenUsageWindow
from smarter.apps.api.v1.contract.models import (
    OpenApiPathItem,
    OpenApiSchema,
    OpenApiTag,
    RestApiErrorResponse,
)
from smarter.apps.api.v1.contract.openapi.builders import (
    ApiFamily,
    integer_id,
    json_response,
    plural,
    query,
    rest_operation,
    rest_read,
    with_article,
)

ACCOUNTS = ApiFamily(
    name=namespace,
    resource=SAMKinds.ACCOUNT.value.lower(),
    urlconf="smarter.apps.account.api.v1.urls",
    description="The {plural}, their users and contacts. For superusers.",
)
"""The accounts' family.

Its routes also serve the user's own token usage and data exports, tagged :data:`TAG_USAGE`.
"""

TAG_USAGE = "usage"
"""The tag of the user's own token usage and data exports, which are not an app's family, but the account app's."""

USAGE_TAG = OpenApiTag(name=TAG_USAGE, description="The user's own token usage and data exports.")
"""The document's tag of the user's own token usage and data exports."""


def account_paths() -> dict[str, OpenApiPathItem]:
    """
    The accounts' REST reads, relative to the server's ``/api/v1``.

    Only superusers may call them. Each of the four resources, the accounts, their users, the user profiles
    (each user's membership of an account) and the account contacts, has a list and a retrieve by id.

    :returns: The paths, e.g. ``{"/accounts/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    family = ACCOUNTS

    def list_and_retrieve(
        name: str, resource: str, suffix: str, id_name: str, list_description: str, item: str
    ) -> dict[str, OpenApiPathItem]:
        capitalized = with_article(resource, capitalize=True)
        return {
            family.path(suffix): OpenApiPathItem(
                get=rest_read(
                    f"{name}_list",
                    f"List {plural(resource)}",
                    list_description,
                    family.tag,
                    item,
                    many=True,
                    parameters=[],
                )
            ),
            family.path(f"{suffix}{{{id_name}}}/"): OpenApiPathItem(
                get=rest_read(
                    f"{name}_retrieve",
                    capitalized,
                    f"{capitalized}, by its id.",
                    family.tag,
                    item,
                    many=False,
                    parameters=[integer_id(id_name, f"The {resource}'s id.")],
                )
            ),
        }

    account = family.resource
    return {
        **list_and_retrieve(
            family.name, account, "", f"{family.name}_id", f"Every {account}.", AccountApiAccountDetail.__name__
        ),
        **list_and_retrieve("user", "user", "users/", "user_id", "Every user.", AccountApiUserDetail.__name__),
        **list_and_retrieve(
            "user_profile",
            "user profile",
            "user-profiles/",
            "user_profile_id",
            f"Every user profile: each user's membership of {with_article(account)}.",
            AccountApiProfile.__name__,
        ),
        **list_and_retrieve(
            "contact",
            f"{account} contact",
            "contacts/",
            f"{account}_contact_id",
            f"Every {account}'s contacts, who receive its notices.",
            AccountApiContact.__name__,
        ),
    }


OWN_DATA = "Requires an api key. Every user may call it, for their own data only."
"""The note of the operations on the requesting user's own data: their token usage and data exports."""


def usage_paths() -> dict[str, OpenApiPathItem]:
    """
    The requesting user's own token usage and data exports, relative to the server's ``/api/v1``.

    They are under ``/accounts/``, whose other reads are for superusers, but every user may call them.

    :returns: The paths, e.g. ``{"/accounts/usage/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    family = ACCOUNTS
    tag = TAG_USAGE
    # A list[str] is not a JsonValue, whose lists are invariant list[JsonValue].
    windows: list[OpenApiSchema] = []
    for window in TokenUsageWindow.WINDOWS:
        windows.append(window)
    start = rest_operation(
        "data_export_start",
        "Start a data export",
        "Start building a zip file of the manifest of every resource that the user owns, in every account "
        "they belong to, with Secrets' values redacted. A link to it is emailed to the user when it is ready. "
        "Answers 202 with the new export, 200 with the export that is already in progress, and 429 when the "
        f"user has no email address or has started too many exports today. {OWN_DATA}",
        tag,
        DataExportStatusResponse.__name__,
        parameters=[],
        status="202",
        error="An error, e.g. 401 without a valid api key.",
    )
    start.responses["202"] = json_response("The export, which was started now.", DataExportStatusResponse.__name__)
    start.responses["200"] = json_response("The export that is already in progress.", DataExportStatusResponse.__name__)
    start.responses["429"] = json_response(
        "Refused: the user has no email address to send the link to, or has started too many exports today. The "
        "detail says which. Retrying doesn't help until tomorrow.",
        RestApiErrorResponse.__name__,
    )
    return {
        family.path("usage/"): OpenApiPathItem(
            get=rest_read(
                "token_usage",
                "Token usage",
                "The tokens and cost of the user's LLM requests over a window of time, one point per hour, day or "
                "month, oldest first, counting the current hour's charges. Cached for five minutes.",
                tag,
                TokenUsageSeries.__name__,
                many=False,
                parameters=[
                    query(
                        "periodicity",
                        "The window: e.g. 24_hours is the current hour and the 23 before it.",
                        {"type": "string", "enum": windows, "default": TokenUsageWindow.DEFAULT},
                    )
                ],
                note=OWN_DATA,
                success="The window's points.",
            )
        ),
        family.path("data-exports/"): OpenApiPathItem(
            get=rest_read(
                "data_export_overview",
                "Data exports",
                "What the user may export: the address that the link is emailed to, how long the link works, how "
                "many exports are left today, and the latest export.",
                tag,
                DataExportOverviewResponse.__name__,
                many=False,
                parameters=[],
                note=OWN_DATA,
                success="The overview.",
            ),
            post=start,
        ),
        family.path("data-exports/{export_id}/"): OpenApiPathItem(
            get=rest_read(
                "data_export_retrieve",
                "A data export",
                "A data export's progress, by its id.",
                tag,
                DataExportStatusResponse.__name__,
                many=False,
                parameters=[integer_id("export_id", "The export's id.")],
                note=OWN_DATA,
                success="The export's progress.",
            )
        ),
    }


__all__ = ["ACCOUNTS", "OWN_DATA", "TAG_USAGE", "USAGE_TAG", "account_paths", "usage_paths"]
