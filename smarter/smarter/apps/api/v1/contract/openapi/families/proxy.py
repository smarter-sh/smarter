"""The Proxies' list, under ``/api/v1/proxy/``.

Their passthroughs are the LLM providers' own apis.
"""

from smarter_types import SAMKinds

from smarter.apps.api.v1.contract.models import OpenApiPathItem
from smarter.apps.api.v1.contract.openapi.builders import (
    API_KEY_ONLY,
    ApiFamily,
    rest_read,
)
from smarter.apps.proxy.const import namespace
from smarter.apps.proxy.contract.models import ProxyApiProxies

PROXIES = ApiFamily(
    name=namespace,
    resource=SAMKinds.PROXY.value,
    urlconf="smarter.apps.proxy.api.v1.urls",
    description="The {plural} that the user may use. Served only when the platform enables {plural} "
    "(SMARTER_ENABLE_PROXY).",
    mount=namespace,
    resources="Proxies",
)
"""The Proxies' family, whose routes are mounted at its app's name, in the singular.

Its plural is given: inflect adds only an s to a capitalized Proxy.
"""


def proxy_paths() -> dict[str, OpenApiPathItem]:
    """
    The Proxies' list, relative to the server's ``/api/v1``.

    Their passthroughs are the providers' apis.

    :returns: The paths, e.g. ``{"/proxy/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    family = PROXIES
    return {
        family.path(): OpenApiPathItem(
            get=rest_read(
                family.operation_id("list"),
                f"List {family.plural}",
                f"The {family.plural} that the user may use, with their urls. Send a provider's requests to "
                f"{family.a}'s url, with a Smarter api key, and the {family.resource} forwards them with the "
                "provider's.",
                family.tag,
                ProxyApiProxies.__name__,
                many=False,
                parameters=[],
                note=API_KEY_ONLY,
            )
        ),
    }


__all__ = ["PROXIES", "proxy_paths"]
