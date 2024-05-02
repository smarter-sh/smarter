# pylint: disable=W0613
"""Smarter API command-line interface 'apply' view"""

from http import HTTPStatus

from django.http import HttpResponse, JsonResponse

from smarter.common.exceptions import SmarterExceptionBase, error_response_factory
from smarter.lib.drf.view_helpers import SmarterTokenAuthentication


class CliDescribeApiView(SmarterTokenAuthentication):
    """Smarter API command-line interface 'apply' view"""

    def post(self, request):
        """Post method for PluginManifestView."""
        try:
            data = {"status": "ok"}
            return HttpResponse(data=data, status=HTTPStatus.OK)
        except NotImplementedError as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.NOT_IMPLEMENTED)
        except SmarterExceptionBase as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.BAD_REQUEST)
        # pylint: disable=W0718
        except Exception as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.INTERNAL_SERVER_ERROR)
