"""Reverse names for the dropzone views."""

from smarter.common.utils import to_snake_case

from .const import namespace
from .view import DropzoneView


class DropzoneReverseNames:
    """A class to hold the names of the dropzone views for easy reference throughout the codebase."""

    namespace = namespace

    dropzone = to_snake_case(DropzoneView.__name__)
