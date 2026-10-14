"""
Enumeration classes for the ImageSearchPlugin manifest models.

.. note::

    **Experimental.** The ImageSearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental.
"""

from smarter.common.enum import SmarterEnumAbstract


class ImageSearchSafeSearch(SmarterEnumAbstract):
    """Brave Image Search filtering of adult content, for the ``safesearch`` search parameter."""

    OFF = "off"
    """No filtering, except for illegal content."""
    STRICT = "strict"
    """Drops all adult content.

    Brave's default.
    """


class ImageSearchFileType(SmarterEnumAbstract):
    """
    Image file types, for the ``fileType`` filter.

    The Brave Image Search API cannot filter by file type, so Smarter filters its results, by
    the extension of each image url, or else by the Content-Type of its response.
    """

    JPG = "jpg"
    PNG = "png"
    GIF = "gif"
    SVG = "svg"
    WEBP = "webp"
    AVIF = "avif"
    BMP = "bmp"
    ICO = "ico"


FILE_TYPE_EXTENSIONS: dict[str, str] = {
    "jpg": ImageSearchFileType.JPG.value,
    "jpeg": ImageSearchFileType.JPG.value,
    "png": ImageSearchFileType.PNG.value,
    "gif": ImageSearchFileType.GIF.value,
    "svg": ImageSearchFileType.SVG.value,
    "webp": ImageSearchFileType.WEBP.value,
    "avif": ImageSearchFileType.AVIF.value,
    "bmp": ImageSearchFileType.BMP.value,
    "ico": ImageSearchFileType.ICO.value,
}
"""Image url file extensions, and their file types."""

FILE_TYPE_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": ImageSearchFileType.JPG.value,
    "image/jpg": ImageSearchFileType.JPG.value,
    "image/png": ImageSearchFileType.PNG.value,
    "image/gif": ImageSearchFileType.GIF.value,
    "image/svg+xml": ImageSearchFileType.SVG.value,
    "image/webp": ImageSearchFileType.WEBP.value,
    "image/avif": ImageSearchFileType.AVIF.value,
    "image/bmp": ImageSearchFileType.BMP.value,
    "image/x-icon": ImageSearchFileType.ICO.value,
    "image/vnd.microsoft.icon": ImageSearchFileType.ICO.value,
}
"""Response Content-Types, and their file types."""
