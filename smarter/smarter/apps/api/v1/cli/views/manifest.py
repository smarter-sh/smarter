# pylint: disable=W0613
"""Smarter API command-line interface 'apply' view"""

from http import HTTPStatus

from django.http import JsonResponse

from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterExceptionBase, error_response_factory
from smarter.lib.drf.view_helpers import SmarterUnauthenticatedAPIView


class CliManifestExampleApiView(SmarterUnauthenticatedAPIView):
    """Smarter API command-line interface 'apply' view"""

    def post(self, request, kind: str = None):
        """Get method for PluginManifestView."""
        filename = kind + ".yaml" if kind else "plugin.yaml"
        try:
            data = {"filepath": f"https://{smarter_settings.environment_cdn_domain}/cli/example-manifests/{filename}"}
            return JsonResponse(data=data, status=HTTPStatus.OK)
        except NotImplementedError as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.NOT_IMPLEMENTED)
        except SmarterExceptionBase as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.BAD_REQUEST)
        # pylint: disable=W0718
        except Exception as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.INTERNAL_SERVER_ERROR)
