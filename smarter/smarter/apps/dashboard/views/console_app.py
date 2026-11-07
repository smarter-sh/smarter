"""
The single-page console's page: Django answers each path that has moved into the console with its index.html.

``@smarter/console`` is built by Vite into ``static/react/@smarter/console/``, and ``collectstatic`` copies it
into ``STATIC_ROOT``, as it does every React app's build. Until the console moves to its own host (phase 4 of
ADR-035), Django serves its ``index.html`` at the paths of the pages that have moved, e.g. ``/login/``, and the
console's router shows the page. A path keeps its url name, so that emails, settings and templates that reverse
it keep working. See ``docs/spa-migration.md``.

While ``SMARTER_STATIC_FILES_ON_CDN`` is on, the page's scripts and styles come from the environment's CDN: the
page's ``/static/`` urls become ``STATIC_URL``'s, and the scripts load their chunks relative to themselves. The page
itself, the cookies and the api stay on the platform's host. ``initialize_platform`` uploads the files after a
deployment's new pods start, so until it has uploaded this build, the page keeps its ``/static/`` urls, which the
server itself serves from the image (:func:`console_on_cdn`).

A visitor who isn't signed in gets the page without its splash (:func:`with_silent_splash`): they are on their
way to a sign-in page, which shows without it.
"""

import re
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
from smarter.lib.django.static_storage import is_uploaded, mark_uploaded

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)

CONSOLE_INDEX_PATH = Path("react") / "@smarter" / "console" / "index.html"
"""The console's page, relative to ``STATIC_ROOT``."""

BUILT_STATIC_URL = "/static/"
"""The prefix of the urls of the console's built page, which Vite's ``base`` sets."""


CONSOLE_SCRIPT = re.compile(r'<script type="module"[^>]* src="/static/(react/@smarter/console/assets/[^"]+\.js)"')
"""The console's main script in its built page, relative to the static files' root."""


def console_script(html: str) -> Optional[str]:
    """
    The console's main script, which names its build: Vite gives it the hash of its content.

    :param html: The built page.
    :returns: Its name relative to the static files' root, e.g. ``react/@smarter/console/assets/index-DlE53XQD.js``,
        or None for a page that has none.
    """
    match = CONSOLE_SCRIPT.search(html)
    if match is None:
        return None
    return match.group(1)


def console_on_cdn(html: str) -> bool:
    """
    Whether the console's page loads its scripts and styles from the CDN.

    :param html: The built page.
    :returns: True while ``STATIC_URL`` is the CDN's and this build is on its bucket; False otherwise, when the
        server serves them from ``/static/``.
    """
    if settings.STATIC_URL == BUILT_STATIC_URL:
        return False
    script = console_script(html)
    if script is None:
        return False
    return is_uploaded(script)


def mark_console_uploaded() -> Optional[str]:
    """
    Record that the console's build is on the CDN's bucket.

    ``initialize_platform`` calls it once it has uploaded the static files.

    :returns: The build's main script, or None when the console isn't built.
    """
    html = console_index_html()
    if html is None:
        return None
    script = console_script(html)
    if script is None:
        return None
    mark_uploaded(script)
    return script


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


SPLASH_ELEMENT = '<div id="smarter-splash"'
"""The start of the splash's element in the console's built page."""

SILENT_SPLASH_ELEMENT = '<div id="smarter-splash" class="smarter-splash-silent"'
"""The same, with the class that hides the splash: the console's index.html defines it."""


def with_silent_splash(html: str) -> str:
    """
    The console's page, with its splash hidden.

    The splash shows while the console loads a signed-in user's session and first page. A visitor who isn't
    signed in is on their way to a sign-in page, whatever the path, which shows as soon as its stylesheets
    have loaded, without the splash. The page's own inline script does the same by path, for the sign-in
    paths only: it can't tell that a visitor of ``/dashboard/`` isn't signed in.

    :param html: The built page.
    :returns: The page, with the splash's element marked silent, or unchanged when it has no splash.
    """
    silent = html.replace(SPLASH_ELEMENT, SILENT_SPLASH_ELEMENT, 1)
    return silent


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

        A visitor who isn't signed in gets it without the splash (:func:`with_silent_splash`).

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
        page = html
        if console_on_cdn(html):
            page = with_static_url(page, settings.STATIC_URL)
        if not request.user.is_authenticated:
            page = with_silent_splash(page)
        return HttpResponse(page, content_type="text/html; charset=utf-8")
