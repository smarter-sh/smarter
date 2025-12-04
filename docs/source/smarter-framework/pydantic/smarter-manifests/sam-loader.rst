SAMLoader
====================

SAMLoader is a lightweight utility class for loading and parsing Smarter Api Manifest (SAM) files into Pydantic models.
It provides a simple interface for reading manifest files, validating their contents, and converting them
into lightweight structured data models that can be used for initializing SAM Pydantic models.

Usage:
  .. code-block:: python

    from smarter.apps.account.manifest.models.secret.model import (
        SAMSecret,
        SAMSecretMetadata,
        SAMSecretSpec,
    )
    from smarter.lib.manifest.loader import SAMLoader

    # initialize the loader from a yaml file.
    loader = SAMLoader(manifest_path="path/to/manifest.yaml")

    # initialize a SAM Pydantic model from the loader.
    self._manifest = SAMSecret(
        apiVersion=self.loader.manifest_api_version,
        kind=self.loader.manifest_kind,
        metadata=SAMSecretMetadata(**self.loader.manifest_metadata),
        spec=SAMSecretSpec(**self.loader.manifest_spec),
    )

.. automodule:: smarter.lib.manifest.loader
   :members:
   :undoc-members:
   :inherited-members:
