"""
The sanitizer of the SVG that the Smarter Doodle Artist draws.

The artist is an LLM, so its SVG is untrusted, whatever its system prompt says. The sign-in page
shows it with ``<img>``, which runs no scripts and loads nothing, and the artwork's url is served
with a sandboxing Content-Security-Policy; this module is the third layer. It keeps only what a
flat, decorative drawing needs, by allowlist:

- elements: ``svg``, ``g``, ``path``, ``rect``, ``circle``, ``ellipse``, ``line``, ``polyline``,
  ``polygon`` and ``style``. Anything else, e.g. ``script``, ``foreignObject``, ``image``, ``a``,
  ``use``, ``text`` or an SMIL ``animate``, is removed with its children.
- attributes: geometry, paint, ``transform`` and ``class``. Every ``on*`` handler, ``href``,
  ``style`` and ``id`` is removed, and a value that contains ``url(``, ``javascript:`` or ``data:``.
- styles: one ``<style>`` of css rules and keyframes, without ``@import``, ``url(``, ``expression``
  or markup, whose class and keyframe names start with the theme's prefix.

The result must still be an SVG of the base scene's ``viewBox`` with something left to draw.
"""

import re
import xml.etree.ElementTree as ET  # nosec B405: only serializes; parsing uses defusedxml

from smarter.common.exceptions import SmarterValueError

from .artwork import parse_svg
from .const import MAX_GENERATED_SVG_LENGTH, SVG_NAMESPACE

ALLOWED_ELEMENTS = frozenset(["svg", "g", "path", "rect", "circle", "ellipse", "line", "polyline", "polygon", "style"])
"""The elements that a generated SVG may have."""

ALLOWED_ATTRIBUTES = frozenset(
    [
        "d",
        "x",
        "y",
        "x1",
        "y1",
        "x2",
        "y2",
        "cx",
        "cy",
        "r",
        "rx",
        "ry",
        "width",
        "height",
        "points",
        "fill",
        "fill-opacity",
        "stroke",
        "stroke-width",
        "stroke-opacity",
        "stroke-linecap",
        "stroke-linejoin",
        "stroke-dasharray",
        "opacity",
        "transform",
        "class",
    ]
)
"""The attributes that a generated SVG's elements may have, besides the root's ``viewBox``."""

FORBIDDEN_VALUE = re.compile(r"url\s*\(|javascript:|data:|expression\s*\(", re.IGNORECASE)
"""Text that no attribute value may contain."""

FORBIDDEN_CSS = re.compile(r"@import|url\s*\(|expression\s*\(|javascript:|<|behavior\s*:", re.IGNORECASE)
"""Text that a generated ``<style>`` may not contain."""

ALLOWED_CSS_PROPERTIES = frozenset(
    [
        "animation",
        "animation-name",
        "animation-duration",
        "animation-delay",
        "animation-timing-function",
        "animation-iteration-count",
        "animation-direction",
        "animation-fill-mode",
        "transform",
        "transform-origin",
        "transform-box",
        "opacity",
    ]
)
"""The css properties that a generated ``<style>`` may set: its animations, and nothing else."""

MAX_ELEMENTS = 200
"""The most elements that a generated SVG may have."""


def local_name(tag: str) -> str:
    """
    Return an element's name without its namespace.

    :param tag: The element's tag, e.g. ``{http://www.w3.org/2000/svg}rect``.
    :returns: Its name, e.g. ``rect``, or the tag itself if it isn't in the SVG namespace.
    :rtype: str
    """
    prefix = f"{{{SVG_NAMESPACE}}}"
    if tag.startswith(prefix):
        return tag[len(prefix) :]
    return tag


def css_blocks(css: str) -> list[tuple[str, str]]:
    """
    Split css into its top-level blocks.

    :param css: The css.
    :returns: Each block's header and body, e.g. ``(".rd-sway", "animation: rd-sway 4s infinite;")``.
    :rtype: list[tuple[str, str]]
    :raises ValueError: If the braces don't match, or text is left outside a block.
    """
    blocks = []
    depth = 0
    header = ""
    header_start = 0
    body_start = 0
    for position, character in enumerate(css):
        if character == "{":
            if depth == 0:
                body_start = position + 1
                header = css[header_start:position]
            depth += 1
        elif character == "}":
            depth -= 1
            if depth < 0:
                raise ValueError("unbalanced braces")
            if depth == 0:
                blocks.append((header.strip(), css[body_start:position]))
                header_start = position + 1
    if depth != 0:
        raise ValueError("unbalanced braces")
    if css[header_start:].strip():
        raise ValueError("text outside a block")
    return blocks


def declarations_are_allowed(body: str) -> bool:
    """
    Whether a css rule's declarations set only :data:`ALLOWED_CSS_PROPERTIES`.

    :param body: The rule's body, e.g. ``transform: rotate(3deg); opacity: 0.5``.
    :returns: True if every declaration is allowed.
    :rtype: bool
    """
    for declaration in body.split(";"):
        if not declaration.strip():
            continue
        if ":" not in declaration:
            return False
        name = declaration.split(":", 1)[0].strip().lower()
        if name not in ALLOWED_CSS_PROPERTIES:
            return False
    return True


def clean_style(css: str, prefix: str) -> str:
    """
    Return a generated ``<style>``'s css, if it is safe.

    Every top-level rule must be a class selector, or a list of them, whose names start with the
    theme's prefix, or a ``@keyframes`` rule whose name does, so that it can't restyle the base
    scene. Rules set only the properties of an animation.

    :param css: The css.
    :param prefix: The theme's prefix, which every class and keyframe name must start with.
    :returns: The css, or an empty string if it isn't safe.
    :rtype: str
    """
    if FORBIDDEN_CSS.search(css):
        return ""
    name = rf"{re.escape(prefix)}-[-_a-zA-Z0-9]+"
    class_selectors = re.compile(rf"^\.{name}(\s*,\s*\.{name})*$")
    keyframes = re.compile(rf"^@keyframes\s+{name}$")
    keyframe_step = re.compile(r"^(from|to|\d{1,3}(\.\d+)?%)(\s*,\s*(from|to|\d{1,3}(\.\d+)?%))*$")
    try:
        blocks = css_blocks(css)
    except ValueError:
        return ""
    for header, body in blocks:
        if class_selectors.match(header):
            if not declarations_are_allowed(body):
                return ""
            continue
        if not keyframes.match(header):
            return ""
        try:
            steps = css_blocks(body)
        except ValueError:
            return ""
        for step, step_body in steps:
            if not keyframe_step.match(step):
                return ""
            if not declarations_are_allowed(step_body):
                return ""
    return css


def clean_element(element: ET.Element, prefix: str) -> None:
    """
    Remove an element's disallowed attributes and children, recursively.

    :param element: The element, which is allowed.
    :param prefix: The theme's prefix, for its styles and classes.
    """
    for name in list(element.attrib):
        value = element.attrib[name]
        keep = name in ALLOWED_ATTRIBUTES
        if FORBIDDEN_VALUE.search(value):
            keep = False
        if name == "class" and not all(token.startswith(f"{prefix}-") for token in value.split()):
            keep = False
        if not keep:
            del element.attrib[name]

    for child in list(element):
        child_name = local_name(child.tag)
        if child_name not in ALLOWED_ELEMENTS or child_name == "svg":
            element.remove(child)
            continue
        if child_name == "style":
            css = clean_style(child.text or "", prefix)
            if not css:
                element.remove(child)
                continue
            child.attrib.clear()
            child.text = css
            for grandchild in list(child):
                child.remove(grandchild)
            continue
        clean_element(child, prefix)


def sanitize_svg(svg: str, prefix: str) -> str:
    """
    Return a generated SVG, with only what a decorative drawing needs.

    :param svg: The SVG that the artist answered with.
    :param prefix: The theme's prefix, two letters, which its css names must start with.
    :returns: The sanitized SVG, ready for :func:`~smarter.apps.doodle.artwork.compose_svg`.
    :rtype: str
    :raises SmarterValueError: If it is too long, not an SVG of the base scene's ``viewBox``, has
        too many elements, or has nothing left to draw.
    """
    if len(svg) > MAX_GENERATED_SVG_LENGTH:
        raise SmarterValueError(f"The SVG has {len(svg)} characters, more than {MAX_GENERATED_SVG_LENGTH}.")
    root = parse_svg(svg)
    count = sum(1 for _ in root.iter())
    if count > MAX_ELEMENTS:
        raise SmarterValueError(f"The SVG has {count} elements, more than {MAX_ELEMENTS}.")

    viewbox = root.get("viewBox")
    clean_element(root, prefix)
    root.attrib.clear()
    root.set("viewBox", str(viewbox))

    drawn = 0
    for element in root.iter():
        name = local_name(element.tag)
        if name in ("svg", "g", "style"):
            continue
        drawn += 1
    if drawn == 0:
        raise SmarterValueError("The SVG has nothing left to draw.")

    clean = ET.tostring(root, encoding="unicode")
    return clean


def extract_svg(text: str) -> str:
    """
    Return the SVG in an LLM's answer, without the prose or code fence around it.

    :param text: The answer.
    :returns: The text from the first ``<svg`` to the last ``</svg>``.
    :rtype: str
    :raises SmarterValueError: If the answer has no SVG.
    """
    start = text.find("<svg")
    end = text.rfind("</svg>")
    if start == -1 or end == -1 or end < start:
        raise SmarterValueError("The answer has no <svg> element.")
    svg = text[start : end + len("</svg>")]
    return svg


__all__ = ["extract_svg", "sanitize_svg"]
