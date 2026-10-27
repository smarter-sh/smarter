"""
Load an installed extension's code into the running process.

Extensions are installed at run time, on a platform whose app, worker and beat processes
run in many pods. The archive of each :class:`~smarter.apps.llmtool.models.ExtensionVersion`
is stored in the database, so each process loads an extension the first time it needs it:

1. **Materialize**: the archive is extracted to
   ``<tempdir>/smarter-extensions/<slug>/<version>-<sha256 prefix>/``, once per pod. It is
   extracted to a temporary directory and renamed into place, so that two processes that
   extract it at the same time cannot see a partial copy.
2. **Import**: the package is imported under a namespace that is unique to the version and
   its contents, ``smarter_extensions.<slug>.v<version>_<sha256 prefix>.<package>``. An
   update imports the new version beside the old one, rather than reloading modules, which
   Python does not do reliably: a tool call that is running finishes on the old code. Old
   modules stay in memory until the process restarts.

An extension's own modules must import each other with relative imports
(``from .models import WeatherArguments``), because the package is not on ``sys.path``.
"""

import importlib
import importlib.util
import inspect
import os
import re
import shutil
import sys
import tempfile
import threading
import traceback
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .archive import ExtensionArchive
from .exceptions import SmarterExtensionLoadError
from .lifecycle import SmarterExtensionLifecycle
from .manifest import ExtensionManifest
from .protocol import SmarterExtensionTool

if TYPE_CHECKING:
    from smarter.apps.llmtool.models import ExtensionVersion

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.EXTENSION_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

NAMESPACE = "smarter_extensions"
"""The top-level module under which every extension's code is imported."""
MARKER = ".smarter-extension-sha256"
"""The file, in a materialized extension's directory, that holds the sha256 of the archive it came from."""
SHA_PREFIX_LENGTH = 12


def extensions_root() -> Path:
    """The directory into which extension archives are extracted."""
    return Path(tempfile.gettempdir()) / "smarter-extensions"


def identifier(text: str) -> str:
    """Return ``text`` as a Python identifier, e.g. ``1.2.0`` as ``1_2_0``."""
    return re.sub(r"[^A-Za-z0-9_]", "_", text)


@dataclass
class LoadedExtension:
    """
    An extension version whose code is imported into this process.

    :param slug: The extension's slug.
    :param version: The version.
    :param sha256: The sha256 of its archive.
    :param manifest: Its manifest.
    :param module_name: The full name under which its package is imported.
    :param tools: Its tool classes, by tool name.
    :param lifecycle: Its lifecycle hooks class, if it has one.
    :param path: The directory that holds its extracted archive.
    """

    slug: str
    version: str
    sha256: str
    manifest: ExtensionManifest
    module_name: str
    path: Path
    tools: dict[str, type[SmarterExtensionTool]] = field(default_factory=dict)
    lifecycle: Optional[type[SmarterExtensionLifecycle]] = None

    def entry_point(self, entry: str) -> object:
        """
        Return the object that an entry point, ``<module>:<attribute>``, names.

        :param entry: e.g. ``weather.tools:GetWeather``.
        """
        module_path, attribute = entry.split(":", 1)
        package = self.manifest.smarter.package
        full_module = self.module_name + module_path[len(package) :]
        module = importlib.import_module(full_module)
        try:
            return getattr(module, attribute)
        except AttributeError as e:
            raise SmarterExtensionLoadError(f"{entry}: {full_module} has no attribute {attribute}") from e


_loaded: dict[tuple[str, str], LoadedExtension] = {}
_lock = threading.RLock()


def module_name_for(manifest: ExtensionManifest, sha256: str) -> str:
    """
    Return the full name under which an extension version's package is imported.

    :param manifest: The version's manifest.
    :param sha256: The sha256 of its archive.
    :returns: e.g. ``smarter_extensions.weather.v1_2_0_0123456789ab.weather``.
    """
    return ".".join(
        [
            NAMESPACE,
            identifier(manifest.slug),
            f"v{identifier(manifest.version)}_{sha256[:SHA_PREFIX_LENGTH]}",
            manifest.smarter.package,
        ]
    )


def materialize(archive: ExtensionArchive) -> Path:
    """
    Extract an archive into this pod's extensions directory, unless it is already there.

    :param archive: The archive.
    :returns: The directory that holds the archive's files.
    """
    manifest = archive.manifest
    target = extensions_root() / manifest.slug / f"{identifier(manifest.version)}-{archive.sha256[:SHA_PREFIX_LENGTH]}"
    marker = target / MARKER
    if marker.is_file() and marker.read_text(encoding="utf-8").strip() == archive.sha256:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
    try:
        archive.extract_to(staging)
        (staging / MARKER).write_text(archive.sha256, encoding="utf-8")
        if target.exists():
            # an earlier extraction was interrupted, or the directory was tampered with.
            shutil.rmtree(target, ignore_errors=True)
        try:
            os.rename(staging, target)
        except OSError:
            # another process renamed its copy into place first.
            if not (marker.is_file() and marker.read_text(encoding="utf-8").strip() == archive.sha256):
                raise
    finally:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
    logger.info("%s.materialize() extracted %s %s to %s", logger_prefix, manifest.slug, manifest.version, target)
    return target


def ensure_namespace(module_name: str) -> None:
    """Create the empty parent packages of ``module_name`` in ``sys.modules``, if they do not exist."""
    parts = module_name.split(".")
    for i in range(1, len(parts)):
        name = ".".join(parts[:i])
        if name not in sys.modules:
            module = types.ModuleType(name, "Smarter Extensions namespace.")
            module.__path__ = []  # type: ignore[attr-defined]
            sys.modules[name] = module


def import_package(module_name: str, package_dir: Path) -> types.ModuleType:
    """
    Import a package from a directory, under a given full name.

    :param module_name: The full name, e.g. ``smarter_extensions.weather.v1_0_0_0123456789ab.weather``.
    :param package_dir: The package's directory, which holds its ``__init__.py``.
    :returns: The package's module.
    """
    if module_name in sys.modules:
        return sys.modules[module_name]
    ensure_namespace(module_name)
    spec = importlib.util.spec_from_file_location(
        module_name, package_dir / "__init__.py", submodule_search_locations=[str(package_dir)]
    )
    if spec is None or spec.loader is None:
        raise SmarterExtensionLoadError(f"cannot import {package_dir}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        forget_modules(module_name)
        raise
    return module


def forget_modules(module_name: str) -> None:
    """Remove a package and its submodules from ``sys.modules``."""
    for name in [name for name in sys.modules if name == module_name or name.startswith(module_name + ".")]:
        del sys.modules[name]


def load_archive(archive: ExtensionArchive) -> LoadedExtension:
    """
    Import an extension archive's code into this process, and find its tools and lifecycle hooks.

    Loading the same archive again returns the extension that is already loaded.

    :param archive: The archive.
    :returns: The loaded extension.
    :raises SmarterExtensionLoadError: If the code cannot be imported, or its tools are not valid.
    """
    manifest = archive.manifest
    key = (manifest.slug, archive.sha256)
    with _lock:
        if key in _loaded:
            return _loaded[key]
        path = materialize(archive)
        module_name = module_name_for(manifest, archive.sha256)
        loaded = LoadedExtension(
            slug=manifest.slug,
            version=manifest.version,
            sha256=archive.sha256,
            manifest=manifest,
            module_name=module_name,
            path=path,
        )
        try:
            import_package(module_name, path / manifest.smarter.package)
            for entry in manifest.smarter.tools:
                tool = loaded.entry_point(entry)
                if not (inspect.isclass(tool) and issubclass(tool, SmarterExtensionTool)):
                    raise SmarterExtensionLoadError(f"tool {entry} is not a SmarterExtensionTool subclass")
                problems = tool.problems()
                if problems:
                    raise SmarterExtensionLoadError(f"tool {entry} is not valid: {'; '.join(problems)}")
                if tool.name in loaded.tools:
                    raise SmarterExtensionLoadError(f"two tools are named {tool.name}")
                loaded.tools[tool.name] = tool
            if manifest.smarter.lifecycle:
                lifecycle = loaded.entry_point(manifest.smarter.lifecycle)
                if not (inspect.isclass(lifecycle) and issubclass(lifecycle, SmarterExtensionLifecycle)):
                    raise SmarterExtensionLoadError(
                        f"lifecycle {manifest.smarter.lifecycle} is not a SmarterExtensionLifecycle subclass"
                    )
                loaded.lifecycle = lifecycle
        except SmarterExtensionLoadError:
            forget_modules(module_name)
            raise
        # an extension's import can fail in any way at all.
        # pylint: disable=broad-exception-caught
        except Exception as e:
            forget_modules(module_name)
            detail = "".join(traceback.format_exception_only(type(e), e)).strip()
            logger.error(
                "%s.load_archive() could not import %s %s: %s",
                logger_prefix,
                manifest.slug,
                manifest.version,
                traceback.format_exc(),
            )
            raise SmarterExtensionLoadError(
                f"{manifest.slug} {manifest.version} could not be imported: {detail}"
            ) from e
        _loaded[key] = loaded
        logger.info(
            "%s.load_archive() loaded %s %s as %s with tools %s",
            logger_prefix,
            manifest.slug,
            manifest.version,
            module_name,
            sorted(loaded.tools),
        )
        return loaded


def load_version(version: "ExtensionVersion") -> LoadedExtension:
    """
    Import an installed extension version's code into this process.

    The archive is read from the database only the first time a process loads the version.

    :param version: The installed version.
    :returns: The loaded extension.
    :raises SmarterExtensionLoadError: If the code cannot be imported, or its tools are not valid.
    """
    key = (version.extension.slug, version.sha256)
    with _lock:
        if key in _loaded:
            return _loaded[key]
        # the archive may have been deferred by the query that fetched the version.
        archive_bytes = bytes(type(version).objects.values_list("archive", flat=True).get(pk=version.pk))
        return load_archive(ExtensionArchive(archive_bytes))


def unload(slug: str) -> None:
    """
    Forget every loaded version of an extension, e.g. after it is uninstalled.

    The modules stay in ``sys.modules``, so a tool call that is running is not affected.

    :param slug: The extension's slug.
    """
    with _lock:
        for key in [key for key in _loaded if key[0] == slug]:
            del _loaded[key]


__all__ = [
    "LoadedExtension",
    "extensions_root",
    "load_archive",
    "load_version",
    "materialize",
    "module_name_for",
    "unload",
]
