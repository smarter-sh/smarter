"""
The extensions' REST reads and actions, under ``/api/v1/extensions/``: what the web console's Extensions pages do.

Every user may read the extensions that their account may use. Only superusers may act on them.
"""

from typing import Optional

from smarter.apps.api.v1.contract.models import (
    OpenApiMediaType,
    OpenApiOperation,
    OpenApiParameter,
    OpenApiPathItem,
    OpenApiRequestBody,
    OpenApiSchema,
)
from smarter.apps.api.v1.contract.openapi.builders import (
    SUPERUSER_OPERATION_ERROR,
    ApiFamily,
    json_body,
    path_string,
    query,
    rest_operation,
    rest_read,
)
from smarter.apps.llmtool.extension.contract import (
    ActionResponse,
    AvailabilityRequest,
    ConfigureRequest,
    ExtensionDetailResponse,
    ExtensionListResponse,
    InstallRequest,
    RegistryResponse,
    RollbackRequest,
)
from smarter.apps.llmtool.extension.urls import namespace

EXTENSIONS = ApiFamily(
    name=namespace,
    resource=namespace,
    urlconf="smarter.apps.llmtool.extension.api.v1.urls",
    description="The {plural}: what every user's account may use, and their management by superusers.",
)
"""The extensions' family.

Its resource is its name: the descriptions write it in lowercase.
"""

EXTENSION_READ = (
    "Requires an api key. A user who is not a superuser sees only the extensions that their account may use, and "
    "receives their settings, the accounts that may use them and the platform admin's Secrets as empty lists, and "
    "who installed each version as null."
)
"""The note of the extensions' reads."""

EXTENSION_ACTION = "Only superusers may call it: others get a 403."
"""The note of the extensions' actions."""


def extension_paths() -> dict[str, OpenApiPathItem]:
    """
    The extensions' REST reads and actions, relative to the server's ``/api/v1``.

    They are what the web console's Extensions pages do. Every user may read the extensions that their account
    may use. Only superusers may act on them.

    :returns: The paths, e.g. ``{"/extensions/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    family = EXTENSIONS
    resource = family.resource
    tag = family.tag
    slug = path_string("slug", f"The {resource}'s slug, e.g. weather.")

    def action(
        operation_id: str,
        summary: str,
        description: str,
        parameters: list[OpenApiParameter],
        request_body: Optional[OpenApiRequestBody] = None,
    ) -> OpenApiOperation:
        return rest_operation(
            operation_id,
            summary,
            f"{description} {EXTENSION_ACTION}",
            tag,
            ActionResponse.__name__,
            parameters=parameters,
            request_body=request_body,
            error=SUPERUSER_OPERATION_ERROR,
        )

    archive: OpenApiSchema = {
        "type": "object",
        "properties": {
            "archive": {
                "type": "string",
                "contentMediaType": "application/zip",
                "description": f"The {resource}'s .zip archive, of at most 10 MiB.",
            }
        },
        "required": ["archive"],
    }
    return {
        family.path(): OpenApiPathItem(
            get=rest_read(
                family.operation_id("list"),
                f"List {family.plural}",
                f"The installed {family.plural}, by display name, whether the registry is enabled, and how many updates "
                "it has.",
                tag,
                ExtensionListResponse.__name__,
                many=False,
                parameters=[],
                note=EXTENSION_READ,
                success="The installed extensions.",
            )
        ),
        family.path("registry/"): OpenApiPathItem(
            get=rest_read(
                family.operation_id("registry"),
                f"The {resource} registry",
                f"The registry's {family.plural}, with what each offers on this platform: install, update, or nothing, "
                "and why. Read from the cached index, unless a superuser asks to refresh it.",
                tag,
                RegistryResponse.__name__,
                many=False,
                parameters=[
                    query(
                        "refresh",
                        "Download the registry's index again, rather than read the cache. Superusers only.",
                        {"type": "boolean", "default": False},
                    )
                ],
                note=EXTENSION_READ,
                success="The registry's extensions.",
            )
        ),
        family.path("check-updates/"): OpenApiPathItem(
            post=action(
                family.operation_id("check_updates"),
                f"Check for {resource} updates",
                f"Download the registry's index, and record each installed {resource}'s newest compatible version.",
                [],
            )
        ),
        family.path("install/"): OpenApiPathItem(
            post=action(
                family.operation_id("install"),
                f"Install {family.a}",
                f"Install, or update, {family.a} from the registry. It is installed disabled: configure its "
                "settings, then enable it.",
                [],
                json_body(InstallRequest.__name__, f"The {resource}'s slug, and optionally its version."),
            )
        ),
        family.path("upload/"): OpenApiPathItem(
            post=action(
                family.operation_id("upload"),
                f"Upload {family.a}",
                f"Install, or update, {family.a} from its .zip archive, as multipart/form-data. It is installed "
                "disabled.",
                [],
                OpenApiRequestBody(
                    required=True,
                    content={"multipart/form-data": OpenApiMediaType(schema_=archive)},
                ),
            )
        ),
        family.path("{slug}/"): OpenApiPathItem(
            get=rest_read(
                family.operation_id("retrieve"),
                family.a_capitalized,
                f"An installed {resource}: its documentation, tools, settings, versions, resources, switches and "
                "availability.",
                tag,
                ExtensionDetailResponse.__name__,
                many=False,
                parameters=[slug],
                note=EXTENSION_READ,
                success="The extension.",
            )
        ),
        family.path("{slug}/enable/"): OpenApiPathItem(
            post=action(
                family.operation_id("enable"),
                f"Enable {family.a}",
                f"Enable the {resource}, after checking that it is compatible, that it loads, and that its required "
                "settings are set. Its tools are then offered to the LLMClients that use it.",
                [slug],
            )
        ),
        family.path("{slug}/disable/"): OpenApiPathItem(
            post=action(family.operation_id("disable"), f"Disable {family.a}", f"Disable the {resource}.", [slug])
        ),
        family.path("{slug}/update/"): OpenApiPathItem(
            post=action(
                family.operation_id("update"),
                f"Update {family.a}",
                f"Install the registry's newest compatible version of the {resource}.",
                [slug],
            )
        ),
        family.path("{slug}/rollback/"): OpenApiPathItem(
            post=action(
                family.operation_id("rollback"),
                f"Roll {family.a} back",
                f"Make one of the {resource}'s earlier installed versions the one that runs.",
                [slug],
                json_body(RollbackRequest.__name__, f"The id of the version, from the {resource}'s versions."),
            )
        ),
        family.path("{slug}/configure/"): OpenApiPathItem(
            post=action(
                family.operation_id("configure"),
                f"Configure {family.a}",
                f"Change some of the {resource}'s settings. A secret setting is given a value, which is saved "
                "encrypted in a Secret of the platform admin, or one of the platform admin's Secrets, or neither, "
                "which clears it. Settings that are left out don't change.",
                [slug],
                json_body(ConfigureRequest.__name__, "The settings' new values, by name."),
            )
        ),
        family.path("{slug}/availability/"): OpenApiPathItem(
            post=action(
                family.operation_id("availability"),
                f"Set {family.a}'s availability",
                f"Make the {resource} available to every account, or to the given accounts only.",
                [slug],
                json_body(AvailabilityRequest.__name__, "Every account, or the ids of the accounts."),
            )
        ),
        family.path("{slug}/uninstall/"): OpenApiPathItem(
            post=action(
                family.operation_id("uninstall"),
                f"Uninstall {family.a}",
                f"Uninstall the {resource}, and delete its versions and settings. The response's extension is null.",
                [slug],
            )
        ),
    }


__all__ = ["EXTENSIONS", "EXTENSION_ACTION", "EXTENSION_READ", "extension_paths"]
