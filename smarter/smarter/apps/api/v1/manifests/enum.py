"""
The kinds of Smarter Application Manifest (SAM), and their icons in the web console.

:class:`SAMKinds` is the single definition of which kinds exist, and of the order in which manifests
of several kinds are applied (:meth:`SAMKinds.apply_order`). It is defined in the
`smarter-types <https://docs.smarter-types.smarter.sh/>`__ package, which the platform and its Python
SDK share, and is re-exported here. To add a kind, add it to ``SAMKinds`` in smarter-types first,
with its place in the apply order, then give it an icon in :data:`SAM_KIND_ICONS`.
"""

from typing import Union

from smarter_types import SAMKinds

SAM_KIND_ICON_DEFAULT = "abstract-26"
"""The icon of a kind that has none of its own in :data:`SAM_KIND_ICONS`, e.g. an Extension, which isn't a SAM kind."""

SAM_KIND_ICONS: dict[str, str] = {
    # plugins
    SAMKinds.STATIC_PLUGIN.value: "document",
    SAMKinds.API_PLUGIN.value: "code",
    SAMKinds.SKILL_PLUGIN.value: "wrench",
    SAMKinds.SQL_PLUGIN.value: "file-sheet",
    SAMKinds.WEBSEARCH_PLUGIN.value: "magnifier",
    SAMKinds.IMAGE_SEARCH_PLUGIN.value: "picture",
    # connections
    SAMKinds.API_CONNECTION.value: "router",
    SAMKinds.SQL_CONNECTION.value: "data",
    # account resources
    SAMKinds.ACCOUNT.value: "bank",
    SAMKinds.AUTH_TOKEN.value: "key",
    SAMKinds.BUDGET.value: "wallet",
    SAMKinds.USER.value: "profile-circle",
    SAMKinds.SECRET.value: "lock-2",
    SAMKinds.GUARDRAIL.value: "shield-tick",
    # prompt resources
    SAMKinds.PROMPT.value: "message-text-2",
    SAMKinds.LLM_CLIENT.value: "artificial-intelligence",
    SAMKinds.CUSTOM_DOMAIN.value: "share",
    SAMKinds.LLM_HOST.value: "technology-4",
    SAMKinds.LLM_HOST_COMPUTE.value: "cube-3",
    SAMKinds.MCP_CLIENT.value: "switch",
    SAMKinds.ORCHESTRATOR.value: "category",
    # provider, proxy and vectorstore resources
    SAMKinds.PROVIDER.value: "cloud",
    SAMKinds.PROXY.value: "exit-right-corner",
    SAMKinds.VECTORSEARCH.value: "filter-search",
    SAMKinds.VECTORSTORE.value: "cube-2",
}
"""
The icon of each SAM kind in the web console: the name of a `Keen Icons <https://keenthemes.com/keenicons>`__.

icon, without its ``ki-`` prefix, which the console's global stylesheet provides, e.g. ``<i class="ki-outline
ki-lock-2"></i>`` for a Secret. Each kind has its own. See :func:`sam_kind_icon`.
"""


def sam_kind_icon(kind: Union[str, SAMKinds]) -> str:
    """
    Return the web console's icon of a kind of resource, e.g. for the cards of an LLMClient's architecture.

    The icon is a `Keen Icons <https://keenthemes.com/keenicons>`__ name, without its ``ki-`` prefix, which
    the web console's global stylesheet provides.

    .. code-block:: python

        sam_kind_icon(SAMKinds.SECRET)  # "lock-2", i.e. <i class="ki-outline ki-lock-2"></i>
        sam_kind_icon("sqlplugin")  # "file-sheet"
        sam_kind_icon("Extension")  # "abstract-26", the default: an Extension isn't a SAM kind

    :param kind: The kind, as a member or its value, in any case.
    :type kind: Union[str, SAMKinds]
    :returns: The icon's name, or :data:`SAM_KIND_ICON_DEFAULT` for a kind that isn't a SAM kind.
    :rtype: str
    """
    value = kind.value if isinstance(kind, SAMKinds) else str(kind)
    icons = {key.lower(): icon for key, icon in SAM_KIND_ICONS.items()}
    return icons.get(value.lower(), SAM_KIND_ICON_DEFAULT)


__all__ = ["SAM_KIND_ICONS", "SAM_KIND_ICON_DEFAULT", "SAMKinds", "sam_kind_icon"]
