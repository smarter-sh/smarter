"""
The artwork of a doodle: a theme's props, drawn on the base scene.

The base scene, ``static/doodle/base.svg``, is a Smarter LLMClient's chat window and the resources
around it: a plugin, a guardrail, a vectorstore, a secret and its manifest. It has an empty group,
``<g id="doodle-props"/>``, and a theme's props, an SVG of the same ``viewBox``, are moved into
it. The props decorate the scene: lanterns in the sky, a pumpkin on the ground, a hat on the chat
window. They are drawn around the scene, not over it.

The browser shows the result with ``<img>``, in which an SVG can't run scripts or load anything.
"""

import hashlib
import xml.etree.ElementTree as ET  # nosec B405: only builds and serializes; parsing uses defusedxml

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import fromstring

from smarter.common.exceptions import SmarterValueError

from .const import BASE_SCENE_PATH, PROPS_PLACEHOLDER_ID, SVG_NAMESPACE, VIEWBOX

ET.register_namespace("", SVG_NAMESPACE)

STILL_STYLE = "<style>*{animation:none !important;}</style>"
"""A style that stops every css animation, for :func:`still_svg`."""


def svg_tag(name: str) -> str:
    """
    Return an SVG element's qualified tag, as ElementTree names it.

    :param name: The element's name, e.g. ``g``.
    :returns: The tag, e.g. ``{http://www.w3.org/2000/svg}g``.
    :rtype: str
    """
    return f"{{{SVG_NAMESPACE}}}{name}"


def parse_svg(svg: str) -> ET.Element:
    """
    Parse an SVG document, safely.

    :param svg: The document.
    :returns: Its root element.
    :rtype: ET.Element
    :raises SmarterValueError: If it isn't well-formed XML, or its root isn't an ``<svg>`` of the
        base scene's ``viewBox``.
    """
    try:
        root = fromstring(svg)
    except ET.ParseError as e:
        raise SmarterValueError(f"The SVG isn't well-formed: {e}") from e
    except DefusedXmlException as e:
        raise SmarterValueError(f"The SVG declares entities or a DTD, which aren't allowed: {e}") from e
    if root.tag != svg_tag("svg"):
        raise SmarterValueError(f"The root element is {root.tag}, not an svg in the {SVG_NAMESPACE} namespace.")
    viewbox = root.get("viewBox")
    if viewbox != VIEWBOX:
        raise SmarterValueError(f"The SVG's viewBox is {viewbox}, not {VIEWBOX}.")
    return root


def read_base_scene() -> str:
    """
    Read the base scene.

    :returns: The base scene's SVG.
    :rtype: str
    """
    with open(BASE_SCENE_PATH, encoding="utf-8") as file:
        return file.read()


def compose_svg(props_svg: str, title: str) -> str:
    """
    Draw a theme's props on the base scene.

    :param props_svg: The props, an SVG of the base scene's ``viewBox``. Empty for none.
    :param title: The image's accessible title, e.g. the theme's alt text.
    :returns: The doodle's SVG.
    :rtype: str
    :raises SmarterValueError: If the props, or the base scene, aren't valid.
    """
    scene = parse_svg(read_base_scene())
    placeholder = None
    for element in scene.iter(svg_tag("g")):
        if element.get("id") == PROPS_PLACEHOLDER_ID:
            placeholder = element
            break
    if placeholder is None:
        raise SmarterValueError(f"The base scene has no <g id={PROPS_PLACEHOLDER_ID!r}>.")

    title_element = scene.find(svg_tag("title"))
    if title_element is None:
        title_element = ET.Element(svg_tag("title"))
        scene.insert(0, title_element)
    title_element.text = title

    if props_svg.strip():
        props = parse_svg(props_svg)
        for child in list(props):
            placeholder.append(child)

    svg = ET.tostring(scene, encoding="unicode")
    return svg


def still_svg(svg: str) -> str:
    """
    Return a doodle's SVG without its animations.

    :param svg: The doodle's SVG.
    :returns: The same SVG, with a last style that stops every animation.
    :rtype: str
    """
    closing_tag = "</svg>"
    position = svg.rfind(closing_tag)
    if position == -1:
        return svg
    still = svg[:position] + STILL_STYLE + svg[position:]
    return still


def svg_sha256(svg: str) -> str:
    """
    Return the hash of an SVG, which names its artwork.

    :param svg: The SVG.
    :returns: Its SHA-256, in hex.
    :rtype: str
    """
    digest = hashlib.sha256(svg.encode("utf-8"))
    return digest.hexdigest()


__all__ = ["compose_svg", "parse_svg", "read_base_scene", "still_svg", "svg_sha256"]
