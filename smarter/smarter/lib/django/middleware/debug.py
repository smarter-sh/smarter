"""Debug middleware for logging the type of the response returned by the view."""

from collections.abc import Awaitable

from django.http import HttpRequest, HttpResponseBase

from smarter.common.mixins import SmarterMiddlewareMixin
from smarter.common.mixins.helper_mixin import SmarterHelperMixin
from smarter.lib import logging
from smarter.lib.django.waffle.switches import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.MIDDLEWARE_LOGGING])
logger.debug(
    "%s is %s",
    logging.formatted_text(__name__ + ".SmarterDebugMiddleware"),
    SmarterHelperMixin().formatted_state_ready,
)


class MiddlewareDebugMiddleware(SmarterMiddlewareMixin):
    """Middleware that logs the type of the response returned by the view."""

    def __call__(self, request: HttpRequest) -> HttpResponseBase | Awaitable[HttpResponseBase]:

        if self.async_mode:
            return self.__acall__(request)

        if self.deserves_amnesty(request.path):
            return self.get_response(request)

        logger.debug("%s.__call__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)

        response = super().__call__(request)
        logger.debug("type(response)=%s, response=%s", type(response), response)
        if not isinstance(response, HttpResponseBase):
            raise TypeError(
                f"Middleware chain expects HttpResponseBase, but returned an invalid response of {type(response)}"
            )

        return response

    async def __acall__(self, request: HttpRequest) -> HttpResponseBase:

        logger.debug("%s.__acall__(): Request received: %s %s", self.formatted_class_name, request.method, request.path)
        response = await super().__acall__(request)
        logger.debug("type(response)=%s, response=%s", type(response), response)

        if not isinstance(response, HttpResponseBase):
            raise TypeError(
                f"Middleware chain expects HttpResponseBase, but returned an invalid response of {type(response)}"
            )

        return await super().__acall__(request)

    @property
    def formatted_class_name(self) -> str:
        """
        Return the formatted class name for logging purposes.

         This method constructs a formatted class name string that includes the module name, class name, and instance ID. It is used to provide a more readable and informative class name in logs, which can help with debugging and tracing the flow of requests through the middleware.

         The formatted class name follows the pattern: "module.ClassName[instance_id]". For example, if the module is "smarter.lib.django.middleware.debug" and the class is "MiddlewareDebugMiddleware", the formatted class name might look like "smarter.lib.django.middleware.debug.MiddlewareDebugMiddleware[12345678]".

         :return: The formatted class name as a string.
         :rtype: str
        """
        class_name = f"{__name__}.{self.__class__.__name__}[{id(self)}]"
        return self.formatted_text(class_name)
