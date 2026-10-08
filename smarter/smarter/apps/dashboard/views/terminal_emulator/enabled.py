"""Whether users can view their server logs in the browser."""

from functools import wraps
from typing import Callable

from django.http import Http404, HttpRequest, HttpResponse

from smarter.common.conf import smarter_settings
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active


def server_logs_enabled() -> bool:
    """
    Whether users can view their server logs in the browser.

    This decides whether the web console's sidebar has a Server Logs item, whether Smarter Chat's
    Console has a Server Logs tab, and whether the Server Logs page and its log stream are found.
    See :func:`require_server_logs`.

    A user's logs are published to their own log stream only by
    :class:`smarter.lib.logging.middleware.SmarterRequestLogContextMiddleware`, so the logs are
    viewable only while its waffle switch,
    :attr:`SmarterWaffleSwitches.ENABLE_WEB_CONSOLE_SERVER_LOGS`, is active. Otherwise the
    stream would stay empty.

    :returns: True if ``smarter_settings.enable_dashboard_server_logs`` is set and the switch is active.
    :rtype: bool
    """
    return smarter_settings.enable_dashboard_server_logs and switch_is_active(
        SmarterWaffleSwitches.ENABLE_WEB_CONSOLE_SERVER_LOGS
    )


def require_server_logs(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """
    Make a Server Logs view a 404 while server logs are disabled.

    This decorates the Server Logs page and its log stream. The url patterns are registered when Django starts, so the waffle switch is checked on each
    request instead, and takes effect as soon as it changes. See :func:`server_logs_enabled`.

    :param view: The view.
    :returns: The view, which raises :class:`django.http.Http404` while server logs are disabled.
    :rtype: Callable[..., HttpResponse]
    """

    @wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not server_logs_enabled():
            raise Http404("Server logs are disabled.")
        return view(request, *args, **kwargs)

    return wrapper
