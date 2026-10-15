"""
Render an extension's documentation, written in reStructuredText, as HTML.

An extension documents itself in its package's module docstring, and optionally in more
pages in its package's ``docs/`` directory (``.rst`` or ``.md``). They are rendered when the
extension is installed, and shown in the admin console.

Documentation comes from the extension's author, so it is rendered safely: raw HTML, file
inclusion and remote images are disabled, and Markdown's raw HTML is escaped.
"""

import html

import markdown
from docutils.core import publish_parts

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.EXTENSION_LOGGING])
logger_prefix = logging.formatted_text(__name__)

SAFE_DOCUTILS_SETTINGS = {
    "raw_enabled": False,
    "file_insertion_enabled": False,
    "report_level": 5,
    "halt_level": 5,
    "warning_stream": False,
    "input_encoding": "unicode",
    "output_encoding": "unicode",
    "doctitle_xform": False,
    "initial_header_level": 3,
}


def render_rst(text: str) -> str:
    """
    Render reStructuredText as an HTML fragment.

    :param text: The reStructuredText.
    :returns: The HTML body, or the text in a ``<pre>`` if it cannot be rendered.
    """
    if not text.strip():
        return ""
    try:
        return publish_parts(source=text, writer="html5", settings_overrides=SAFE_DOCUTILS_SETTINGS)["body"]
    # docutils raises many kinds of exceptions for malformed input.
    # pylint: disable=broad-exception-caught
    except Exception as e:
        logger.warning("%s.render_rst() could not render reStructuredText: %s", logger_prefix, e)
        return f"<pre>{html.escape(text)}</pre>"


def render_markdown(text: str) -> str:
    """
    Render Markdown as an HTML fragment, with any raw HTML escaped.

    :param text: The Markdown.
    :returns: The HTML.
    """
    return markdown.markdown(html.escape(text, quote=False), extensions=["fenced_code", "tables"])


def render_page(filename: str, text: str) -> str:
    """
    Render one documentation page, by its file extension.

    :param filename: e.g. ``usage.rst`` or ``usage.md``.
    :param text: The page's text.
    :returns: The HTML.
    """
    if filename.lower().endswith(".md"):
        return render_markdown(text)
    return render_rst(text)


__all__ = ["render_markdown", "render_page", "render_rst"]
