# pylint: disable=W0613
"""Smarter API command-line interface 'get' view"""
from http import HTTPStatus

from django.http import JsonResponse

from smarter.common.exceptions import error_response_factory
from smarter.lib.manifest.exceptions import SAMBadRequestError

from ...manifests.enum import SAMKinds
from .base import CliBaseApiView


class ApiV1CliGetApiView(CliBaseApiView):
    """Smarter API command-line interface 'get' view"""

    def post(self, request, kind: str, name: str = None):
        """
        post() for 'get' view. Valid urls params:
        'all': boolean = False
        'tags': comma-delimited str = None
        """
        all_objects: bool = request.GET.get("all", False)
        tags: str = request.GET.get("tags", None)

        # Validate the manifest kind: plugins, users, chatbots, chats, etc.
        if kind not in SAMKinds.plural_slugs():
            return JsonResponse(
                error_response_factory(
                    e=SAMBadRequestError(f"Invalid manifest kind '{kind}'. Must be one of {SAMKinds.plural_slugs()}")
                ),
                status=HTTPStatus.BAD_REQUEST,
            )

        return self.broker.get(request, name=name, all_objects=all_objects, tags=tags)
