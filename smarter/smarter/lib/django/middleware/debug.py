"""Debug middleware for logging the type of the response returned by the view."""

from collections.abc import Awaitable
from functools import cached_property

from django.http import HttpRequest, HttpResponseBase

from smarter.common.mixins import SmarterMiddlewareMixin
from smarter.common.mixins.helper_mixin import SmarterHelperMixin
from smarter.lib import logging
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MIDDLEWARE_LOGGING])
logger.debug(
    "%s is %s",
    logging.SmarterFormattedText.text(__name__) + ".MiddlewareDebugMiddleware",
    SmarterHelperMixin().formatted_state_ready,
)


class MiddlewareDebugMiddleware(SmarterMiddlewareMixin):
    """Middleware that logs the type of the response returned by the view."""

    def __call__(self, request: HttpRequest) -> HttpResponseBase | Awaitable[HttpResponseBase]:
        """
        Log a sync request and the type of its response, or hand it to :meth:`__acall__` in async mode.

        An amnesty path goes straight to the next handler, without logging.

        :param request: The incoming request.
        :returns: The response (a coroutine in async mode).
        :raises TypeError: if the middleware chain returned something other than a response.
        """
        if self.async_mode:
            return self.__acall__(request)

        if self.deserves_amnesty(request.path):
            return self.get_response(request)

        logger.debug("%s.__call__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)

        response = super().__call__(request)
        logger.debug(
            "%s.__call__(): type(response)=%s, response=%s", self.formatted_class_name, type(response), response
        )
        if not isinstance(response, HttpResponseBase):
            raise TypeError(
                f"Middleware chain expects HttpResponseBase, but returned an invalid response of {type(response)}"
            )

        return response

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:
        """
        Log an async request and the type of its response.

        :param request: The incoming request.
        :returns: The response.
        :raises TypeError: if the middleware chain returned something other than a response.
        """
        logger.debug("%s.__acall__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)
        response = await super().__acall__(request)
        logger.debug(
            "%s.__acall__(): type(response)=%s, response=%s", self.formatted_class_name, type(response), response
        )

        if not isinstance(response, HttpResponseBase):
            raise TypeError(
                f"Middleware chain expects HttpResponseBase, but returned an invalid response of {type(response)}"
            )

        return response

    @cached_property
    def formatted_class_name(self) -> str:
        """
        Return the formatted class name for logging purposes.

        It names the instance, not a request, in the form ``module.ClassName[instance_id]``, e.g.
        ``smarter.lib.django.middleware.debug.MiddlewareDebugMiddleware[12345678]``.

        :returns: The formatted class name.
        """
        class_name = f"{__name__}.{self.__class__.__name__}[{id(self)}]"
        return self.formatted_text(class_name)
