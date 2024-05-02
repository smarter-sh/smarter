# pylint: disable=W0613
"""Smarter API command-line interface 'apply' view"""

from http import HTTPStatus

from django.http import JsonResponse

from smarter.common.exceptions import SmarterExceptionBase, error_response_factory
from smarter.lib.drf.view_helpers import SmarterTokenAuthentication


class CliDeleteObjectApiView(SmarterTokenAuthentication):
    """Smarter API command-line interface 'apply' view"""

    def delete(self, request):
        try:
            data = {"CliDeleteObjectApiView": "ok"}
            return JsonResponse(data=data, status=HTTPStatus.OK)
        except NotImplementedError as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.NOT_IMPLEMENTED)
        except SmarterExceptionBase as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.BAD_REQUEST)
        # pylint: disable=W0718
        except Exception as e:
            return JsonResponse(error_response_factory(e=e), status=HTTPStatus.INTERNAL_SERVER_ERROR)
