"""The plugins' REST reads, under ``/api/v1/plugins/``: the llmtool app's plugins."""

from smarter_types import SAMKinds

from smarter.apps.api.v1.contract.models import OpenApiPathItem
from smarter.apps.api.v1.contract.openapi.builders import (
    API_KEY_ONLY,
    READ_PERMISSION,
    ApiFamily,
    integer_id,
    rest_read,
)
from smarter.apps.llmtool.contract.models import PluginApiPluginMeta

PLUGIN = SAMKinds.STATIC_PLUGIN.value.lower()
"""A plugin, as the descriptions name it: the kind of a static plugin, in lowercase, e.g. plugin."""

PLUGINS = ApiFamily(
    name=PLUGIN,
    resource=PLUGIN,
    urlconf="smarter.apps.llmtool.api.v1.urls",
    description="The {plural}' REST reads.",
)
"""The plugins' family.

The llmtool app serves it, but its operations are named after its resource.
"""


def plugin_paths() -> dict[str, OpenApiPathItem]:
    """
    The plugins' REST reads, relative to the server's ``/api/v1``.

    :returns: The paths, e.g. ``{"/plugins/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    family = PLUGINS
    resource = family.resource
    return {
        family.path(): OpenApiPathItem(
            get=rest_read(
                family.operation_id("list"),
                f"List {family.plural}",
                f"The {family.plural} that the user owns, newest first: their metadata.",
                family.tag,
                PluginApiPluginMeta.__name__,
                many=True,
                parameters=[],
                note=API_KEY_ONLY,
            )
        ),
        family.path("{plugin_id}/"): OpenApiPathItem(
            get=rest_read(
                family.operation_id("retrieve"),
                family.a_capitalized,
                f"{family.a_capitalized}'s manifest, if the user may read the {resource}. It is served only while "
                "the platform's ALLOW_API_GET switch is active, and answers 405 otherwise.",
                family.tag,
                "SAMManifest",
                many=False,
                parameters=[integer_id("plugin_id", f"The {resource}'s id.")],
                note=READ_PERMISSION,
            )
        ),
    }


__all__ = ["PLUGINS", "plugin_paths"]
