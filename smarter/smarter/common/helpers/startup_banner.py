"""
The banner that the Smarter web server prints when it starts.

It draws the Smarter logo, an infinity loop shaded from orange to yellow, next to the
facts that someone reading a pod's log wants first: the version, the host, the
environment and its url, and the database, cache and Celery broker that this process
talks to. Passwords in those urls are masked.

:func:`print_startup_banner` is called from :mod:`smarter.asgi`. Uvicorn's ``--workers``
imports the application once per worker process, so only the first worker of a
server prints it.
"""

import multiprocessing
import os
import platform
import socket
import sys
import tempfile
from collections.abc import Callable
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

from smarter.lib import logging

logger = logging.getLogger(__name__)
logger_prefix = logging.formatted_text(__name__)

ESC = "\033["
RESET = f"{ESC}0m"
BOLD = f"{ESC}1m"
GRAY = f"{ESC}38;5;245m"
WHITE = f"{ESC}38;5;255m"

LOGO_GRADIENT = (202, 208, 214, 220)
"""256-color codes from left to right, following the logo's orange-to-yellow gradient."""

LOGO = (
    "  ▄████████▄▄        ▄▄████████▄  ",
    "▄███▀▀▀▀▀▀████▄    ▄████▀▀▀▀▀▀███▄",
    "██▀         ▀███▄▄███▀         ▀██",
    "██            ██████            ██",
    "██▄         ▄███▀▀███▄         ▄██",
    "▀███▄▄▄▄▄▄████▀    ▀████▄▄▄▄▄▄███▀",
    "  ▀████████▀▀        ▀▀████████▀  ",
)
"""The Smarter infinity loop, a lemniscate drawn in half-block characters."""

LOGO_WIDTH = len(LOGO[0])
WORDMARK = "S  M  A  R  T  E  R".center(LOGO_WIDTH)
GUTTER = "   "
UNKNOWN = "unknown"


def mask_url(url: str | None) -> str:
    """
    Return a url with its password replaced by ``**``, the way Celery shows its broker.

    :param url: A url such as ``redis://:secret@smarter-redis:6379/1``.
    :returns: The url with the password masked, e.g. ``redis://:**@smarter-redis:6379/1``,
        or ``unknown`` when there is no url.
    """
    if not url:
        return UNKNOWN
    parts = urlsplit(url)
    if parts.password is None:
        return url
    userinfo = f"{parts.username or ''}:**"
    host = parts.hostname or ""
    netloc = f"{userinfo}@{host}" + (f":{parts.port}" if parts.port else "")
    return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))


def _safe(getter: Callable[[], object]) -> str:
    """
    Return ``str(getter())``, or ``unknown`` if it raises.

    A missing or invalid setting must never keep the server from starting.

    :param getter: A function that reads one value for the banner.
    :returns: The value as a string.
    """
    try:
        value = getter()
    except Exception:  # pylint: disable=broad-exception-caught
        return UNKNOWN
    return UNKNOWN if value in (None, "") else str(value)


def _database_url() -> str:
    """
    Return the default database as a url, without its password.

    :returns: e.g. ``mysql://smarter@smarter-mariadb:3306/smarter``.
    """
    from django.conf import settings  # pylint: disable=import-outside-toplevel

    db = settings.DATABASES["default"]
    vendor = db["ENGINE"].rsplit(".", 1)[-1]
    port = f":{db['PORT']}" if db.get("PORT") else ""
    return f"{vendor}://{db.get('USER', '')}@{db.get('HOST', '')}{port}/{db.get('NAME', '')}"


def banner_facts() -> list[tuple[str, str]]:
    """
    Return the configuration that the banner lists, as (label, value) pairs.

    :returns: The labels and values, in the order they are shown.
    """
    from django.conf import settings  # pylint: disable=import-outside-toplevel

    from smarter.common.conf import (  # pylint: disable=import-outside-toplevel
        smarter_settings,
    )

    return [
        ("environment", _safe(lambda: smarter_settings.environment)),
        ("url", _safe(lambda: smarter_settings.environment_url)),
        ("database", _safe(_database_url)),
        ("cache", mask_url(_safe(lambda: settings.CACHES["default"]["LOCATION"]))),
        ("broker", mask_url(_safe(lambda: settings.CELERY_BROKER_URL))),
        ("log level", _safe(lambda: smarter_settings.log_level_name)),
        ("debug", "ON" if getattr(settings, "DEBUG", False) else "OFF"),
        (
            "runtime",
            f"python {_safe(platform.python_version)}  ·  django {_safe(lambda: smarter_settings.django_version)}",
        ),
    ]


def _color_logo_line(line: str) -> str:
    """
    Shade one line of the logo from orange on the left to yellow on the right.

    :param line: A line of :data:`LOGO`.
    :returns: The line with a 256-color code before each change of shade.
    """
    out = []
    current = None
    for column, char in enumerate(line):
        shade = LOGO_GRADIENT[column * len(LOGO_GRADIENT) // LOGO_WIDTH]
        if char != " " and shade != current:
            out.append(f"{ESC}38;5;{shade}m")
            current = shade
        out.append(char)
    out.append(RESET)
    return "".join(out)


def startup_banner(color: bool = True) -> str:
    """
    Build the startup banner: the logo and wordmark on the left, the configuration on the right.

    :param color: Whether to include ANSI color codes.
    :returns: The banner, starting and ending with a newline.
    """
    from smarter.common.conf import (  # pylint: disable=import-outside-toplevel
        smarter_settings,
    )

    facts = banner_facts()
    label_width = max(len(label) for label, _ in facts)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    title = f"smarter@{_safe(socket.gethostname)} v{_safe(lambda: smarter_settings.version)}"
    if color:
        right = [
            f"{BOLD}{WHITE}{title}{RESET}",
            f"{GRAY}{_safe(platform.platform)}  {now}{RESET}",
            "",
        ]
        right += [f"{GRAY}{label.ljust(label_width)}{RESET}  {value}" for label, value in facts]
        left = [_color_logo_line(line) for line in LOGO] + ["", f"{GRAY}{WORDMARK}{RESET}"]
    else:
        right = [title, f"{_safe(platform.platform)}  {now}", ""]
        right += [f"{label.ljust(label_width)}  {value}" for label, value in facts]
        left = list(LOGO) + ["", WORDMARK]

    # The logo sits a line lower than the title, so that it is centered on the text.
    left = [""] + left
    blank = " " * LOGO_WIDTH
    rows = max(len(left), len(right))
    lines = []
    for i in range(rows):
        logo_part = left[i] if i < len(left) and left[i] else blank
        text_part = right[i] if i < len(right) else ""
        lines.append(f" {logo_part}{GUTTER}{text_part}".rstrip())
    return "\n" + "\n".join(lines) + "\n"


def _is_first_worker() -> bool:
    """
    Return whether this process should print the banner.

    A process that wasn't started by :mod:`multiprocessing`, such as ``uvicorn`` without
    ``--workers``, always prints it. Uvicorn's workers are its children, and share a
    parent pid, so the first of them to create a marker file named for that pid prints it.

    :returns: True if this process should print the banner.
    """
    if multiprocessing.parent_process() is None:
        return True
    marker = os.path.join(tempfile.gettempdir(), f"smarter-startup-banner-{os.getppid()}")
    try:
        fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return False
    except OSError:
        return True
    os.close(fd)
    return True


def print_startup_banner() -> None:
    """
    Print the startup banner to stdout, once per server.

    Colors are left out when the ``NO_COLOR`` environment variable is set
    (see https://no-color.org). Any error is logged and swallowed, so that the
    banner can never keep the server from starting.
    """
    try:
        if not _is_first_worker():
            return
        sys.stdout.write(startup_banner(color=not os.environ.get("NO_COLOR")))
        sys.stdout.flush()
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.warning("%s.print_startup_banner() could not print the startup banner: %s", logger_prefix, e)


__all__ = ["mask_url", "banner_facts", "startup_banner", "print_startup_banner"]
