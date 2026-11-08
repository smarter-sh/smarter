"""
An llmclient's manifest: its page, which the single-page console renders, and its JSON, for the workbench.

:class:`LLMClientDetailView` is the page, and :class:`LLMClientManifestEditorView` returns the manifest as JSON for
the Prompt Engineer's Workbench's Manifest tab.
"""

from http import HTTPStatus

from django.http import HttpRequest, HttpResponse, JsonResponse

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.dashboard.views.console_app import ConsoleAppView
from smarter.apps.prompt.views.detailviews.prompt_deployment_view import (
    readable_llmclient,
)
from smarter.lib import logging
from smarter.lib.django import waffle
from smarter.lib.django.views import SmarterAuthenticatedNeverCachedWebView
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PROMPT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class LLMClientManifestEditorView(SmarterAuthenticatedNeverCachedWebView):
    """
    Returns an llmclient's manifest, as JSON, for the manifest editor of the Prompt Engineer's Workbench.

    The workbench, ``@smarter/workbench``, renders the ``@smarter/manifest-editor`` component in its Console's
    "Manifest" tab, and fetches the manifest from this view when the tab is first opened. The manifest is the one
    that the resource api returns, the cli api's describe as the llmclient's owner
    (:func:`smarter.apps.dashboard.resource_detail.manifest_yaml`). The editor saves it with the cli api, as the
    signed-in user, and the workbench then reloads the llmclient's configuration.

    A user who may not read the llmclient gets the same 404 as for an unknown id, by the rule of the workbench's other
    tabs (:func:`~smarter.apps.prompt.views.detailviews.prompt_deployment_view.readable_llmclient`): e.g. another
    account's llmclient, or a staff-only one for a user who is not the platform's staff.

    **Example usage**::

        GET /api/web/prompt/llm-clients/<str:hashed_id>/manifest/
        {"manifest": "apiVersion: smarter.sh/v1\\nkind: LLMClient\\n..."}
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns a formatted string of the class name for logging purposes."""
        class_name = f"{__name__}.{LLMClientManifestEditorView.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Return the llmclient's manifest, as YAML in JSON: ``{"manifest": "<yaml>"}``.

        :param request: The request.
        :type request: django.http.HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: The url's keyword arguments: ``hashed_id``.
        :returns: The manifest; ``{"error": ...}``, a 404, for an unknown llmclient or one that the user may not
            read; or ``{"error": ...}``, a 500, if the llmclient can't be described.
        :rtype: django.http.JsonResponse
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.dashboard.resource_detail import manifest_yaml

        llmclient = readable_llmclient(request, kwargs.get("hashed_id"))
        if llmclient is None:
            logger.debug(
                "%s.get() no llmclient %s for %s", self.formatted_class_name, kwargs.get("hashed_id"), request.user
            )
            return JsonResponse({"error": "LLMClient not found."}, status=HTTPStatus.NOT_FOUND)
        manifest, error = manifest_yaml(SAMKinds.LLM_CLIENT.value, llmclient)
        if manifest is None:
            logger.error("%s.get() could not describe %s: %s", self.formatted_class_name, llmclient, error)
            return JsonResponse({"error": error}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
        return JsonResponse({"manifest": manifest})


class LLMClientDetailView(ConsoleAppView):
    """
    An llmclient's manifest page, ``/workbench/llm-clients/<hashed_id>/manifest/``: the single-page console's.

    The console reads the manifest from the resource api, which finds the llmclient if the user may read it, as for
    every other kind's manifest page. Django keeps this view at the path it served the page at, so that its url name,
    and ``LLMClient.manifest_url``, still reverse.
    """
