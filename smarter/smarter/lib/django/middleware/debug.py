"""
Debug middleware for logging the type of the response returned by the view.
"""

from collections.abc import Awaitable

from django.http import HttpRequest, HttpResponseBase

from smarter.common.mixins import SmarterMiddlewareMixin
from smarter.lib import logging

logger = logging.getSmarterLogger(__name__)


class MiddlewareDebugMiddleware(SmarterMiddlewareMixin):
    """
    Middleware that logs the type of the response returned by the view.
    """

    def __call__(self, request: HttpRequest) -> HttpResponseBase | Awaitable[HttpResponseBase]:

        if self.async_mode:
            return self.__acall__(request)

        if self.deserves_amnesty(request.path):
            return self.get_response(request)

        logger.debug("%s.__call__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)

        response = self.get_response(request)
        logger.debug("type(response)=%s, response=%s", type(response), response)
        if not isinstance(response, HttpResponseBase):
            raise TypeError(
                f"Middleware chain expects HttpResponseBase, but returned an invalid response of {type(response)}"
            )

        return response

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:

        logger.debug("%s.__acall__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)
        response = await self.get_response(request)
        logger.debug("type(response)=%s, response=%s", type(response), response)

        if not isinstance(response, HttpResponseBase):
            raise TypeError(
                f"Middleware chain expects HttpResponseBase, but returned an invalid response of {type(response)}"
            )

        return await super().__acall__(request)

    @property
    def formatted_class_name(self) -> str:
        return logging.formatted_text(f"{__name__}.{self.__class__.__name__}")
