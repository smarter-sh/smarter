"""
The single-page console's page: Django answers each path that has moved into the console with its index.html.

``@smarter/console`` is built by Vite into ``static/react/@smarter/console/``, and ``collectstatic`` copies it
into ``STATIC_ROOT``, as it does every React app's build. Until the console moves to its own host (phase 4 of
ADR-035), Django serves its ``index.html`` at the paths of the pages that have moved, e.g. ``/login/``, and the
console's router shows the page. A path keeps its url name, so that emails, settings and templates that reverse
it keep working. See ``docs/spa-migration.md``.

While ``SMARTER_STATIC_FILES_ON_CDN`` is on, the page's scripts and styles come from the environment's CDN: the
page's ``/static/`` urls become ``STATIC_URL``'s, and the scripts load their chunks relative to themselves. The page
itself, the cookies and the api stay on the platform's host.
"""

from http import HTTPStatus
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie

from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)

CONSOLE_INDEX_PATH = Path("react") / "@smarter" / "console" / "index.html"
"""The console's page, relative to ``STATIC_ROOT``."""

BUILT_STATIC_URL = "/static/"
"""The prefix of the urls of the console's built page, which Vite's ``base`` sets."""


def with_static_url(html: str, static_url: str) -> str:
    """
    The console's page, with its scripts' and styles' urls under ``static_url``.

    :param html: The built page, whose urls start with ``/static/``.
    :param static_url: Django's ``STATIC_URL``, e.g. ``https://cdn.platform.example.com/static/``.
    :returns: The page, with each ``src`` and ``href`` attribute's ``/static/`` replaced by ``static_url``,
        or unchanged while ``static_url`` is ``/static/``.
    """
    if static_url == BUILT_STATIC_URL:
        return html
    for attribute in ("src", "href"):
        built = f'{attribute}="{BUILT_STATIC_URL}'
        served = f'{attribute}="{static_url}'
        html = html.replace(built, served)
    return html


def console_index_html() -> Optional[str]:
    """
    The console's built ``index.html``, from ``STATIC_ROOT``.

    It is read on each request, rather than cached, so that a new build takes effect at once. It is a
    few hundred bytes.

    :returns: The page, or None when the console hasn't been built and collected.
    """
    index_path = Path(settings.STATIC_ROOT) / CONSOLE_INDEX_PATH
    if not index_path.is_file():
        return None
    return index_path.read_text(encoding="utf-8")


@method_decorator(never_cache, name="dispatch")
@method_decorator(ensure_csrf_cookie, name="dispatch")
class ConsoleAppView(View):
    """
    Answer a path that has moved into the single-page console with the console's page.

    The page is never cached, so that a deployment's new build replaces it at once; its scripts and
    styles have hashed names and are cached as other static files are. It sets the CSRF cookie, which the
    console's first POST needs.
    """

    http_method_names = ["get", "head"]

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Return the console's page, whatever the path's arguments, e.g. a password reset link's.

        :param request: The request.
        :returns: The page, or 503 when the console hasn't been built, which ``make react-build`` fixes.
        """
        html = console_index_html()
        if html is None:
            logger.error(
                "%s.ConsoleAppView.get() %s is missing. Run make react-build.",
                logger_prefix,
                Path(settings.STATIC_ROOT) / CONSOLE_INDEX_PATH,
            )
            return HttpResponse(
                "The web console hasn't been built.",
                status=HTTPStatus.SERVICE_UNAVAILABLE,
                content_type="text/plain; charset=utf-8",
            )
        page = with_static_url(html, settings.STATIC_URL)
        return HttpResponse(page, content_type="text/html; charset=utf-8")
