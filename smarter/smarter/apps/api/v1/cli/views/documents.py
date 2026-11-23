# pylint: disable=W0613
"""Smarter API command-line interface 'documents' view."""

from rest_framework.request import Request

from smarter.lib import logging

from .base import CliBaseApiView

logger = logging.getSmarterLogger(__name__)


class ApiV1CliDocumentsApiView(CliBaseApiView):
    """
    The API endpoint of the 'documents' command of the Smarter command-line interface (CLI).

    It lists, adds or removes the documents of a resource that has them, a Vectorstore: see
    :meth:`smarter.apps.vectorstore.manifest.brokers.vectorstore.SAMVectorstoreBroker.documents`. It is
    a Smarter Brokered and Journaled operation. Its body is not a manifest, but the documents to add,
    as multipart/form-data, so the body is never given to the broker as one.

    The response is a JSON object.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this mixin."""
        inherited_class = super().formatted_class_name
        this_class = f".{ApiV1CliDocumentsApiView.__name__}[{id(self)}]"
        return f"{inherited_class}{self.formatted_text(this_class)}"

    def initial(self, request: Request, *args, **kwargs):
        """
        Initialize the view as every cli view is, but without a manifest.

        The base view keeps a JSON or form body as the manifest's data, from which the broker would
        build a manifest. This body is documents to add, so it is left to the broker's ``documents()``.

        :param request: The request.
        """
        super().initial(request, *args, **kwargs)
        self._manifest_data = None

    def post(self, request, kind, *args, **kwargs):
        """
        List, add or remove the documents of the resource named in the ``name`` query parameter.

        Brokered and journaled.

        :param request: The request: optional files, text or a url to add, as multipart/form-data, or a
            ``remove`` query parameter.
        :param kind: The resource's kind, e.g. ``Vectorstore``.
        :returns: The journaled json response.
        """
        logger.debug("called with kind=%s, kwargs=%s", kind, kwargs)
        if self.broker is None:
            raise ValueError(f"No broker found for kind '{kind}' in {self.formatted_class_name}")
        response = self.broker.documents(request=request, kwargs=kwargs)
        return response
