"""Smarter API Plugin Manifest handler"""

import logging
from typing import Any

from smarter.apps.api.v0.manifests.broker import SAMBroker

from .models.plugin import SAMPlugin


logger = logging.getLogger(__name__)


class SAMPluginBroker(SAMBroker):
    """
    Smarter API Plugin Manifest Broker.This class is responsible for
    - loading, validating and parsing the Smarter Api yaml Plugin manifests
    - using the manifest to initialize the corresponding Pydantic model

    The Plugin object provides the generic services for the Plugin, such as
    instantiation, create, update, delete, etc.
    """

    # override the base abstract manifest model with the Plugin model
    _manifest: Any = None

    def __init__(
        self,
        manifest: str = None,
        file_path: str = None,
        url: str = None,
    ):
        # 1.) Load, validate and parse the manifest. The parent will initialize
        # the generic manifest loader class, SAMLoader(), which can then be used to
        # provide initialization data to any kind of manifest model. the loader
        # also performs cursory high-level validation of the manifest, sufficient
        # to ensure that the manifest is a valid yaml file and that it contains
        # the required top-level keys.
        super().__init__(manifest=manifest, file_path=file_path, url=url)

        # 2.) Initialize the Plugin manifest model. SAMPlugin() is a Pydantic model
        # that is used to represent the Smarter API Plugin manifest. The Pydantic
        # model is initialized with the data from the manifest loader, which is
        # generally passed to the model constructor as **data. However, this top-level
        # manifest model has to be explicitly initialized, whereas its child models
        # are automatically cascade-initialized by the Pydantic model, implicitly
        # passing **data to each child's constructor.

        self._manifest = SAMPlugin(
            apiVersion=self.loader.manifest_api_version,
            kind=self.loader.manifest_kind,
            metadata=self.loader.manifest_metadata,
            spec=self.loader.manifest_spec,
            status=self.loader.manifest_status,
        )

    # override the base abstract manifest model with the Plugin model
    @property
    def manifest(self) -> Any:
        return self._manifest
