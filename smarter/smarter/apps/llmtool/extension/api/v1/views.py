"""
The Extensions REST api, under ``/api/v1/extensions/``: what the web console's Extensions pages do, with an api key.

- ``GET extensions/``: the installed extensions that the user may see, and the state of the registry.
- ``GET extensions/registry/``: the registry's extensions. ``?refresh=true`` downloads the index again,
  for a superuser.
- ``POST extensions/check-updates/``: check the registry for updates now.
- ``POST extensions/install/``: install, or update, an extension from the registry, ``{"slug": ..., "version": ...}``.
- ``POST extensions/upload/``: install, or update, an extension from a .zip archive, as multipart/form-data
  with the file ``archive``.
- ``GET extensions/<slug>/``: an extension's detail, and less of it to a user who is not a superuser.
- ``POST extensions/<slug>/enable/``, ``disable/``, ``update/``, ``rollback/``, ``configure/``,
  ``availability/`` and ``uninstall/``: the actions on an extension.

The reads are for every user, who sees only the extensions that their account may use. Everything else is
for superusers only. Each view mixes one of the handlers of :mod:`smarter.apps.llmtool.extension.views`,
which the web console's api uses too, into :class:`ExtensionApiV1View`. The responses are the models of
:mod:`smarter.apps.llmtool.extension.contract`, which the Smarter api's OpenAPI document publishes. Errors
are Django REST framework's ``{"detail": ...}``.
"""

from collections.abc import Mapping

from rest_framework.request import Request
from rest_framework.response import Response

from smarter.apps.llmtool.extension.views import (
    ExtensionApiHandler,
    ExtensionAvailabilityHandler,
    ExtensionCheckUpdatesHandler,
    ExtensionConfigureHandler,
    ExtensionDetailHandler,
    ExtensionDisableHandler,
    ExtensionEnableHandler,
    ExtensionInstallHandler,
    ExtensionListHandler,
    ExtensionRegistryHandler,
    ExtensionRollbackHandler,
    ExtensionUninstallHandler,
    ExtensionUpdateHandler,
    ExtensionUploadHandler,
)
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
)
from smarter.lib.typing import SmarterDictType


# abstract, as are its two subclasses: the concrete views get handle() from the handler that they mix in.
class ExtensionApiV1View(ExtensionApiHandler, SmarterAuthenticatedAPIView):  # pylint: disable=abstract-method
    """
    The base class of the Extensions REST api: an api key, JSON or multipart in, JSON out.

    The data of a GET is its query string, and of a POST its body. Errors are ``{"detail": ...}``.
    """

    def request_data(self, request: Request) -> SmarterDictType:  # type: ignore[override]
        """
        Return the request's query parameters, for a GET, or its parsed body.

        :param request: The request.
        :returns: The data, as a dict.
        """
        data: object
        if request.method == "GET":
            data = request.query_params
        else:
            data = request.data
        if not isinstance(data, Mapping):
            return {}
        result: SmarterDictType = {}
        for key in data:
            result[key] = data[key]
        return result

    def reply(self, request: Request, **kwargs) -> Response:
        """
        Carry out the request with :meth:`respond`, and return its model's JSON or ``{"detail": ...}``.

        :param request: The request.
        :param kwargs: Keyword arguments from the url, e.g. ``slug``.
        :returns: The response.
        """
        status, result = self.respond(request, **kwargs)
        if isinstance(result, str):
            return Response({"detail": result}, status=status)
        return Response(result.to_json(), status=status)


class ExtensionApiV1ReadView(ExtensionApiV1View):  # pylint: disable=abstract-method
    """A read: GET."""

    def get(self, request: Request, *args, **kwargs) -> Response:
        """
        Return the read.

        :param request: The request.
        :param kwargs: Keyword arguments from the url, e.g. ``slug``.
        :returns: The response.
        """
        return self.reply(request, **kwargs)


class ExtensionApiV1ActionView(ExtensionApiV1View):  # pylint: disable=abstract-method
    """An action: POST."""

    def post(self, request: Request, *args, **kwargs) -> Response:
        """
        Carry out the action.

        :param request: The request.
        :param kwargs: Keyword arguments from the url, e.g. ``slug``.
        :returns: The response.
        """
        return self.reply(request, **kwargs)


class ExtensionV1ListView(ExtensionListHandler, ExtensionApiV1ReadView):
    """The installed extensions that the user may see."""


class ExtensionV1RegistryView(ExtensionRegistryHandler, ExtensionApiV1ReadView):
    """The registry's extensions."""


class ExtensionV1DetailView(ExtensionDetailHandler, ExtensionApiV1ReadView):
    """An installed extension."""


class ExtensionV1CheckUpdatesView(ExtensionCheckUpdatesHandler, ExtensionApiV1ActionView):
    """Check the registry for updates now."""


class ExtensionV1InstallView(ExtensionInstallHandler, ExtensionApiV1ActionView):
    """Install, or update, an extension from the registry."""


class ExtensionV1UploadView(ExtensionUploadHandler, ExtensionApiV1ActionView):
    """Install, or update, an extension from an uploaded .zip archive."""


class ExtensionV1EnableView(ExtensionEnableHandler, ExtensionApiV1ActionView):
    """Enable an extension."""


class ExtensionV1DisableView(ExtensionDisableHandler, ExtensionApiV1ActionView):
    """Disable an extension."""


class ExtensionV1UpdateView(ExtensionUpdateHandler, ExtensionApiV1ActionView):
    """Update an extension to the registry's newest compatible version."""


class ExtensionV1RollbackView(ExtensionRollbackHandler, ExtensionApiV1ActionView):
    """Make an earlier version of an extension the one that runs."""


class ExtensionV1ConfigureView(ExtensionConfigureHandler, ExtensionApiV1ActionView):
    """Change some of an extension's settings."""


class ExtensionV1AvailabilityView(ExtensionAvailabilityHandler, ExtensionApiV1ActionView):
    """Change which accounts may use an extension."""


class ExtensionV1UninstallView(ExtensionUninstallHandler, ExtensionApiV1ActionView):
    """Uninstall an extension."""


__all__ = [
    "ExtensionApiV1ActionView",
    "ExtensionApiV1ReadView",
    "ExtensionApiV1View",
    "ExtensionV1AvailabilityView",
    "ExtensionV1CheckUpdatesView",
    "ExtensionV1ConfigureView",
    "ExtensionV1DetailView",
    "ExtensionV1DisableView",
    "ExtensionV1EnableView",
    "ExtensionV1InstallView",
    "ExtensionV1ListView",
    "ExtensionV1RegistryView",
    "ExtensionV1RollbackView",
    "ExtensionV1UninstallView",
    "ExtensionV1UpdateView",
    "ExtensionV1UploadView",
]
