"""
Pydantic models of the JSON that.

:class:`~smarter.lib.django.templatetags.smarter_react_templatetag_manager.SmarterReactTemplateTagManager`
reads and returns.

- :class:`ViteManifest` is a Vite-generated React ``manifest.json``: a map of
  :class:`ViteManifestChunk` keyed by source path. The manager validates the
  file against it when it loads it, and collects an entry point's assets with
  its methods.
- :class:`ReactAppAssets` is what every ``<app>_react_assets`` template tag
  returns: the ordered JS and CSS files that a Django template includes for a
  React app.

The manifest is a third-party shape. :class:`ViteManifestChunk` declares the
fields that Vite documents, and allows extra fields, which newer Vite (or
Rolldown) versions add, so that a Vite upgrade doesn't break page rendering.
Smarter's own addition, the ``_custom`` entry that every package's
``vite.config.ts`` writes after the build, is a :class:`ReactAppBuildInfo`.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SerializerFunctionWrapHandler,
    model_serializer,
    model_validator,
)

from smarter.lib.typing import SmarterDictType

ReactAssetType = Literal["js", "css"]
"""The kinds of asset that a React app's entry point loads."""

BUILD_INFO_KEY = "_custom"
"""The key of the build information that each React package's ``vite.config.ts`` adds to its manifest.json."""


class ViteManifestChunk(BaseModel):
    """
    One entry of a Vite-generated ``manifest.json``: a chunk, or a static asset.

    See https://vite.dev/guide/backend-integration. Extra fields are allowed,
    because Vite and Rolldown add their own.

    Example::

        "index.html": {
            "file": "assets/index.js",
            "name": "index",
            "src": "index.html",
            "isEntry": true,
            "imports": ["_rolldown-runtime.js", "_xterm.js"],
            "css": ["assets/index-DvLY75bJ.css"]
        }
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    file: str = Field(description="The output file of this chunk, relative to the app's static directory.")
    name: Optional[str] = Field(default=None, description="The chunk's name.")
    names: list[str] = Field(default_factory=list, description="The names of a static asset.")
    src: Optional[str] = Field(default=None, description="The chunk's source path.")
    is_entry: bool = Field(default=False, alias="isEntry", description="Whether this chunk is an entry point.")
    is_dynamic_entry: bool = Field(
        default=False, alias="isDynamicEntry", description="Whether this chunk is a dynamic entry point."
    )
    imports: list[str] = Field(default_factory=list, description="The manifest keys of statically imported chunks.")
    dynamic_imports: list[str] = Field(
        default_factory=list, alias="dynamicImports", description="The manifest keys of dynamically imported chunks."
    )
    css: list[str] = Field(default_factory=list, description="The CSS files that this chunk loads.")
    assets: list[str] = Field(default_factory=list, description="The other static files that this chunk references.")


class ReactAppBuildInfo(BaseModel):
    """
    The build information that each React package's ``vite.config.ts`` adds to its manifest.json, as ``_custom``.

    Example::

        "_custom": {
            "buildTime": "2026-10-12T01:09:47.988Z",
            "version": "0.3.0",
            "buildEnv": "production"
        }
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    build_time: datetime = Field(alias="buildTime", description="When the app was built.")
    version: str = Field(description="The version of the app's npm package.")
    build_env: str = Field(alias="buildEnv", description="The build's NODE_ENV, e.g. production.")


class ViteManifest(BaseModel):
    """
    A React app's Vite-generated ``manifest.json``: its chunks, keyed by source path, and Smarter's build information.

    In the file, the build information is the ``_custom`` entry, beside the
    chunks. Validating a manifest.json splits it out into :attr:`build_info`,
    and dumping the model puts it back, so ``model_dump(by_alias=True)`` has the
    file's shape.

    See the example in :mod:`smarter.lib.django.templatetags.smarter_react_templatetag_manager`.
    """

    model_config = ConfigDict(extra="forbid")

    chunks: dict[str, ViteManifestChunk] = Field(description="The manifest's chunks, keyed by source path.")
    build_info: Optional[ReactAppBuildInfo] = Field(
        default=None, description="The ``_custom`` build information, if the package's vite.config.ts adds it."
    )

    @model_validator(mode="before")
    @classmethod
    def split_build_info(cls, data: object) -> object:
        """
        Split a manifest.json's ``_custom`` entry from its chunks.

        Input that already has ``chunks``, e.g. keyword arguments, is left as is.

        :param data: The manifest.json's content.
        :returns: The model's fields.
        :rtype: object
        """
        if not isinstance(data, dict) or "chunks" in data:
            return data
        chunks = dict(data)
        return {"chunks": chunks, "build_info": chunks.pop(BUILD_INFO_KEY, None)}

    @model_serializer(mode="wrap")
    def join_build_info(self, handler: SerializerFunctionWrapHandler) -> SmarterDictType:
        """
        Dump the manifest in the shape of manifest.json, with the build information as its ``_custom`` entry.

        :param handler: Pydantic's default serializer.
        :returns: The chunks, keyed by source path, and ``_custom``.
        :rtype: SmarterDictType
        """
        data = handler(self)
        manifest = dict(data["chunks"])
        if data.get("build_info") is not None:
            manifest[BUILD_INFO_KEY] = data["build_info"]
        return manifest

    def __bool__(self) -> bool:
        """
        Whether the manifest has any chunks.

        :returns: True if the manifest has chunks.
        :rtype: bool
        """
        return bool(self.chunks)

    def entry_key(self) -> Optional[str]:
        """
        Find the key of the manifest's entry point, the first chunk with ``"isEntry": true``.

        :returns: The entry point's key, or None if the manifest has no entry point.
        :rtype: Optional[str]
        """
        return next((key for key, chunk in self.chunks.items() if chunk.is_entry), None)

    def collect_assets(self, key: str, asset_type: ReactAssetType, seen: Optional[set[str]] = None) -> list[str]:
        """
        Recursively collect the JS or CSS files of a chunk and of its static imports.

        A chunk's own files come first, followed by those of each of its
        ``imports``, depth first, in the order they are listed. Each chunk is
        visited once, so circular imports terminate.

        :param key: The manifest key of the chunk to collect assets for.
        :param asset_type: ``"js"`` for the chunks' ``file``, ``"css"`` for their ``css`` files.
        :param seen: The keys already visited, used by the recursion.
        :returns: The asset file paths, relative to the app's static directory.
        :rtype: list[str]
        """
        if seen is None:
            seen = set()
        if key in seen or key not in self.chunks:
            return []
        seen.add(key)

        chunk = self.chunks[key]
        assets = [chunk.file] if asset_type == "js" else list(chunk.css)
        for imported_key in chunk.imports:
            assets.extend(self.collect_assets(key=imported_key, asset_type=asset_type, seen=seen))
        return assets


class ReactAppAssets(BaseModel):
    """
    The ordered JS and CSS files of a React app's entry point, which a Django template includes.

    Every ``<app>_react_assets`` template tag returns one. Templates read its
    attributes, e.g. ``{% for css_file in assets.css %}``.

    Example::

        {
            "js": [
                "assets/index-CZK_Bxxh.js",
                "assets/rolldown-runtime-B3igc2qu.js",
                "assets/xterm-D5XSfLrr.js"
            ],
            "css": [
                "assets/index-58MXwt-L.css",
                "assets/xterm-kHJ-D0s7.css"
            ]
        }
    """

    model_config = ConfigDict(extra="forbid")

    js: list[str] = Field(default_factory=list, description="The JS files, the entry point's first.")
    css: list[str] = Field(default_factory=list, description="The CSS files, the entry point's first.")
