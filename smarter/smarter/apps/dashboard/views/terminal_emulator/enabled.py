"""Whether users can view their server logs, and whether superusers can open a terminal, in the browser."""

from functools import wraps
from typing import Callable

from django.http import Http404, HttpRequest, HttpResponse

from smarter.common.conf import smarter_settings
from smarter.lib.django.waffle import SmarterWaffleSwitches, switch_is_active


def server_logs_enabled() -> bool:
    """
    Whether users can view their server logs in the browser.

    This decides whether the Prompt Passthrough page has a Server Logs tab, whether Smarter Chat's
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


def terminal_enabled() -> bool:
    """
    Whether superusers can open a bash shell in the server's container from the web console.

    This decides whether the sidebar has a Terminal item, and whether the Terminal page, its ticket
    api and its WebSocket are found. Only superusers can use them, even while it is True. See
    :func:`require_terminal` and
    :class:`smarter.apps.dashboard.views.terminal_emulator.api.consumers.TerminalConsumer`.

    :returns: True if ``smarter_settings.enable_web_console_terminal`` is set.
    :rtype: bool
    """
    return smarter_settings.enable_web_console_terminal


def require_terminal(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    """
    Make a Terminal view a 404 while the terminal is disabled, and for every user but a superuser.

    An anonymous request reaches the view, which redirects it to the login page. A signed in user
    who is not a superuser gets a 404, so that the page's existence is not revealed. See
    :func:`terminal_enabled`.

    :param view: The view.
    :returns: The view, which raises :class:`django.http.Http404` while the terminal is disabled,
        or when the user is signed in but is not a superuser.
    :rtype: Callable[..., HttpResponse]
    """

    @wraps(view)
    def wrapper(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not terminal_enabled():
            raise Http404("The terminal is disabled.")
        user = getattr(request, "user", None)
        if getattr(user, "is_authenticated", False) and not getattr(user, "is_superuser", False):
            raise Http404("The terminal is for superusers only.")
        return view(request, *args, **kwargs)

    return wrapper
