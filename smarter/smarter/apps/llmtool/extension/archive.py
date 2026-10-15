"""
A Smarter Extension's archive: the zip file that an administrator installs.

An archive holds a ``pyproject.toml`` (the :class:`~.manifest.ExtensionManifest`) and the
Python package that it names, at the archive's root:

.. code-block:: text

    weather-1.0.0.zip
    ├── pyproject.toml
    ├── README.md            (optional)
    └── weather/
        ├── __init__.py      (its module docstring is the extension's documentation)
        ├── tools.py
        ├── lifecycle.py     (optional install, upgrade and uninstall hooks)
        ├── manifests/       (optional SAM manifests, applied on install, deleted on uninstall)
        ├── static/          (optional assets: icons, images, css, js)
        └── docs/            (optional extra documentation pages, .rst or .md)

An archive whose files are all in one top-level directory, as GitHub's source archives
are, is accepted too: the directory is ignored.

:class:`ExtensionArchive` validates an archive without importing any of its code: it
rejects paths that would escape the extraction directory, links, and archives that are too
large, and it reads the package's docstring by parsing, not importing, ``__init__.py``.
"""

import ast
import hashlib
import io
import os
import stat
import zipfile
from functools import cached_property
from pathlib import Path, PurePosixPath
from typing import Optional

from .exceptions import SmarterExtensionArchiveError, SmarterExtensionManifestError
from .manifest import ExtensionManifest

PYPROJECT = "pyproject.toml"
MAX_ARCHIVE_BYTES = 10 * 1024 * 1024
"""The largest archive, compressed, that can be installed."""
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
"""The largest archive, uncompressed, that can be installed.

Protects against zip bombs.
"""
MAX_FILES = 2000
STATIC_DIRECTORY = "static"
DOCS_DIRECTORY = "docs"
MANIFESTS_DIRECTORY = "manifests"
EXCLUDED_DIRECTORIES = {
    "__pycache__",
    ".git",
    ".github",
    ".venv",
    "venv",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
}
EXCLUDED_SUFFIXES = {".pyc", ".pyo"}
OPTIONAL_ROOT_FILES = ("README.md", "README.rst", "LICENSE", "LICENSE.md", "LICENSE.txt", "CHANGELOG.md")
ZIP_TIMESTAMP = (2000, 1, 1, 0, 0, 0)
"""The timestamp of every file in a built archive, so that building the same source twice gives the same sha256."""


class ExtensionArchive:
    """
    A validated extension archive.

    :param data: The bytes of the zip file.
    :raises SmarterExtensionArchiveError: If the data is not a safe, valid extension archive.
    :raises SmarterExtensionManifestError: If its ``pyproject.toml`` is missing or invalid.

    **Example usage**::

        archive = ExtensionArchive(uploaded_file.read())
        archive.manifest.slug, archive.manifest.version, archive.sha256
        archive.extract_to(Path("/tmp/weather"))
    """

    def __init__(self, data: bytes):
        if len(data) > MAX_ARCHIVE_BYTES:
            raise SmarterExtensionArchiveError(
                f"the archive is {len(data)} bytes; the largest that can be installed is {MAX_ARCHIVE_BYTES}"
            )
        self.data = data
        try:
            self._zip = zipfile.ZipFile(io.BytesIO(data))
        except zipfile.BadZipFile as e:
            raise SmarterExtensionArchiveError(f"the archive is not a zip file: {e}") from e
        self._members: dict[str, zipfile.ZipInfo] = self._validated_members()
        package = self.manifest.smarter.package
        if f"{package}/__init__.py" not in self._members:
            raise SmarterExtensionArchiveError(f"the archive has no {package}/__init__.py")

    def _validated_members(self) -> dict[str, zipfile.ZipInfo]:
        """
        Return the archive's files by their path relative to the archive's root.

        :raises SmarterExtensionArchiveError: If any path is unsafe, or the archive is too large.
        """
        infos = [info for info in self._zip.infolist() if not info.is_dir()]
        if not infos:
            raise SmarterExtensionArchiveError("the archive is empty")
        if len(infos) > MAX_FILES:
            raise SmarterExtensionArchiveError(f"the archive has {len(infos)} files; at most {MAX_FILES} are allowed")
        total = sum(info.file_size for info in infos)
        if total > MAX_UNCOMPRESSED_BYTES:
            raise SmarterExtensionArchiveError(
                f"the archive expands to {total} bytes; at most {MAX_UNCOMPRESSED_BYTES} are allowed"
            )
        for info in infos:
            path = PurePosixPath(info.filename)
            if (
                info.filename.startswith(("/", "\\"))
                or ".." in path.parts
                or "\\" in info.filename
                or ":" in path.parts[0]
            ):
                raise SmarterExtensionArchiveError(f"the archive has an unsafe path: {info.filename}")
            if stat.S_ISLNK(info.external_attr >> 16):
                raise SmarterExtensionArchiveError(f"the archive has a link, which is not allowed: {info.filename}")
        names = [info.filename for info in infos]
        prefix = ""
        if PYPROJECT not in names:
            tops = {PurePosixPath(name).parts[0] for name in names}
            if len(tops) == 1 and f"{next(iter(tops))}/{PYPROJECT}" in names:
                prefix = next(iter(tops)) + "/"
            else:
                raise SmarterExtensionManifestError(f"the archive has no {PYPROJECT} at its root")
        members: dict[str, zipfile.ZipInfo] = {}
        for info in infos:
            relative = info.filename[len(prefix) :]
            if relative in members:
                raise SmarterExtensionArchiveError(f"the archive has two files named {relative}")
            members[relative] = info
        return members

    @cached_property
    def sha256(self) -> str:
        """The hex sha256 of the archive's bytes."""
        return hashlib.sha256(self.data).hexdigest()

    @property
    def names(self) -> list[str]:
        """The paths of the archive's files, relative to its root, sorted."""
        return sorted(self._members)

    def read(self, path: str) -> bytes:
        """
        Return the contents of one of the archive's files.

        :param path: The file's path, relative to the archive's root.
        :raises KeyError: If there is no such file.
        """
        return self._zip.read(self._members[path])

    def read_text(self, path: str) -> Optional[str]:
        """Return a text file's contents, or None if there is no such file or it is not UTF-8."""
        try:
            return self.read(path).decode("utf-8")
        except (KeyError, UnicodeDecodeError):
            return None

    @cached_property
    def manifest(self) -> ExtensionManifest:
        """The archive's parsed ``pyproject.toml``."""
        text = self.read_text(PYPROJECT)
        if text is None:
            raise SmarterExtensionManifestError(f"{PYPROJECT} is not UTF-8 text")
        return ExtensionManifest.from_pyproject(text)

    @cached_property
    def docstring(self) -> str:
        """
        The module docstring of the extension's package: its documentation, in reStructuredText.

        It is read by parsing ``__init__.py``, without importing it.
        """
        source = self.read_text(f"{self.manifest.smarter.package}/__init__.py") or ""
        try:
            return ast.get_docstring(ast.parse(source)) or ""
        except SyntaxError as e:
            raise SmarterExtensionArchiveError(
                f"{self.manifest.smarter.package}/__init__.py has a syntax error: {e}"
            ) from e

    def package_files(self, directory: str) -> list[str]:
        """
        Return the paths, relative to ``<package>/<directory>/``, of the files in one of the package's directories.

        :param directory: e.g. ``static`` or ``docs``.
        """
        prefix = f"{self.manifest.smarter.package}/{directory}/"
        return [name[len(prefix) :] for name in self.names if name.startswith(prefix)]

    def extract_to(self, target: Path) -> None:
        """
        Extract the archive's files into a directory.

        :param target: The directory, which is created if necessary.
        """
        target.mkdir(parents=True, exist_ok=True)
        root = target.resolve()
        for relative, info in self._members.items():
            destination = (target / relative).resolve()
            if root not in destination.parents:
                raise SmarterExtensionArchiveError(f"the archive has an unsafe path: {info.filename}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(self._zip.read(info))


def build_archive(source: Path) -> bytes:
    """
    Build an extension archive from an extension's source directory.

    The archive holds the ``pyproject.toml``, the package it names, and a README, LICENSE
    or CHANGELOG if there is one. Caches, version control and virtual environments are
    left out. The same source always gives the same bytes.

    :param source: The directory that holds ``pyproject.toml``.
    :returns: The archive's bytes.
    :raises SmarterExtensionManifestError: If the directory has no valid ``pyproject.toml``.
    :raises SmarterExtensionArchiveError: If the package directory does not exist.
    """
    pyproject = source / PYPROJECT
    if not pyproject.is_file():
        raise SmarterExtensionManifestError(f"{source} has no {PYPROJECT}")
    manifest = ExtensionManifest.from_pyproject(pyproject.read_text(encoding="utf-8"))
    package_dir = source / manifest.smarter.package
    if not package_dir.is_dir():
        raise SmarterExtensionArchiveError(f"{source} has no package directory {manifest.smarter.package}/")

    files: list[Path] = [pyproject]
    files.extend(source / name for name in OPTIONAL_ROOT_FILES if (source / name).is_file())
    for directory, subdirectories, filenames in os.walk(package_dir):
        subdirectories[:] = sorted(d for d in subdirectories if d not in EXCLUDED_DIRECTORIES)
        files.extend(
            Path(directory) / filename
            for filename in sorted(filenames)
            if Path(filename).suffix not in EXCLUDED_SUFFIXES and not filename.startswith(".")
        )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(path.relative_to(source).as_posix(), date_time=ZIP_TIMESTAMP)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    return buffer.getvalue()


__all__ = ["ExtensionArchive", "build_archive"]
