"""Smarter API Manifest Broker base class."""

from .loader import SAMLoader
from .models import SAM


class SAMBroker:
    """
    Smarter API Manifest Handler ("SAMH") base class. This class is responsible
    for loading, validating and parsing the Smarter Api yaml manifests and then
    using these to initialize the corresponding Pydantic models.
    """

    _manifest: SAM = None
    _loader: SAMLoader = None

    def __init__(
        self,
        account_number: str,
        manifest: str = None,
        file_path: str = None,
        url: str = None,
    ):
        # load, validate and parse the manifest into json
        self._loader = SAMLoader(account_number=account_number, manifest=manifest, file_path=file_path, url=url)

        # initialize the manifest model. this will be the first of two passes. in this iteration
        # we'll initialize the top-level manifest model. the child class overrides manifest with
        # the appropriate model, which will then reinitialize the manifests, but with additional
        # child models. Note that there is only one loader and only one manifest data set.
        self._manifest = SAM(**self.loader.data)

    @property
    def manifest(self) -> SAM:
        return self._manifest

    @property
    def loader(self) -> SAMLoader:
        return self._loader
