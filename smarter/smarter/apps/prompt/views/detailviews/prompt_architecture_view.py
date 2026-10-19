"""
LLMClientArchitectureView returns an llmclient's architecture, for the "Architecture" tab of the workbench's Console.

The tab is in the Prompt Engineer's Workbench, between "Manifest" and "Server Logs". It draws the tree of the
SAM resources that the llmclient is built from: the llmclient, the Provider, plugins, MCPClients, Guardrails and
api key that it uses, and, recursively, what those use, such as Connections and Secrets. Each resource is a
card with its kind, its name and its owner, which opens the resource's manifest page, where its manifest can
be edited. Beneath the tree, the tab suggests what an llmclient that has no Guardrail, no tools or no styles
could add, with links to the web console pages where those resources are browsed. The workbench, the ``@smarter/workbench`` React app, renders the ``@smarter/llmclient-architecture``
component, whose contract is :mod:`smarter.apps.prompt.views.detailviews.architecture_contract`, and fetches the
tree from :class:`LLMClientArchitectureView` when the tab is first opened.
"""

from http import HTTPStatus

from django.http import HttpRequest, HttpResponse, JsonResponse

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.guardrail.urls import GuardrailReverseNames
from smarter.apps.llmclient.manifest.brokers.llmclient import SAMLLMClientBroker
from smarter.apps.llmtool.extension.urls import ExtensionReverseNames
from smarter.apps.llmtool.urls import PluginReverseNames
from smarter.apps.mcpclient.urls import MCPClientReverseNames
from smarter.apps.prompt.views.detailviews.architecture_contract import (
    LLMClientArchitecture,
    LLMClientArchitectureLinks,
)
from smarter.apps.prompt.views.detailviews.prompt_deployment_view import (
    readable_llmclient,
)
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROMPT_LOGGING])


class LLMClientArchitectureView(SmarterAuthenticatedNeverCachedWebView):
    """
    Returns an llmclient's architecture, as JSON, for the "Architecture" tab of the Prompt Engineer's Workbench.

    The architecture is an
    :class:`~smarter.apps.prompt.views.detailviews.architecture_contract.LLMClientArchitecture`: the
    llmclient's :meth:`~smarter.lib.manifest.broker.AbstractBroker.dependency_tree`, a
    :class:`~smarter.lib.manifest.models.SAMDependencyTreeNode`, as the signed-in user may see it (a
    resource that the user may not read has only its kind and record locator), whether its chat is styled,
    and the urls of the web console's Guardrails, Plugins, Extensions and MCPClients pages.

    The response is never cached, so that the tab shows the llmclient as it is when the workbench is
    reloaded. An llmclient that the user may not read is a 404.

    **Example usage**::

        GET /workbench/llm-clients/<str:hashed_id>/architecture/
        {"tree": {"kind": "LLMClient", "name": "stackademy_sql", "owner": "Ada Lovelace (ada)", ...,
                  "children": [{"kind": "SqlPlugin", ...}]},
         "styled": false,
         "links": {"guardrailsUrl": "/guardrail/", ...}}
    """

    http_method_names = ["get"]

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{LLMClientArchitectureView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        The llmclient's architecture: its tree, whether it is styled, and the console's list pages.

        The tree's root is the llmclient of the url's hashed id itself, not one found by its name, which
        users of other accounts may have too.

        :param request: The request.
        :type request: django.http.HttpRequest
        :returns: The architecture, or ``{"error": ...}``, a 404, if the user may not read the llmclient, or there is none.
        :rtype: django.http.JsonResponse
        """
        llmclient = readable_llmclient(request, kwargs.get("hashed_id"))
        if llmclient is None:
            logger.debug(
                "%s.get() no llmclient %s for %s", self.formatted_class_name, kwargs.get("hashed_id"), request.user
            )
            return JsonResponse({"error": "LLMClient not found."}, status=HTTPStatus.NOT_FOUND)
        kind = SAMKinds.LLM_CLIENT.value
        broker = SAMLLMClientBroker(request, name=llmclient.name, kind=kind)
        tree = broker.dependency_tree_node(kind, llmclient, ancestors=frozenset())
        architecture = LLMClientArchitecture(
            tree=tree,
            styled=bool(llmclient.styles),
            links=LLMClientArchitectureLinks(
                guardrails_url=reverse(GuardrailReverseNames.namespace, GuardrailReverseNames.listview),
                plugins_url=reverse(PluginReverseNames.namespace, PluginReverseNames.listview),
                extensions_url=reverse(ExtensionReverseNames.namespace, ExtensionReverseNames.listview),
                mcp_clients_url=reverse(MCPClientReverseNames.namespace, MCPClientReverseNames.listview),
            ),
        )
        logger.debug("%s.get() architecture of %s", self.formatted_class_name, llmclient)
        return JsonResponse(architecture.to_json())
