# pylint: disable=wrong-import-position
"""Base class for testing classes derived from AbstractBroker."""

import logging
import os
from typing import Type

import yaml
from django.http import HttpRequest

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib import json
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.loader import SAMLoader


HERE = os.path.abspath(os.path.dirname(__file__))
logger = logging.getLogger(__name__)


class TestSAMBrokerBaseClass(TestAccountMixin):
    """
    Test the Smarter SAMUserBroker.
    """

    _here: str
    _request: HttpRequest
    _loader: SAMLoader
    _broker: AbstractBroker
    _broker_class: Type[AbstractBroker]
    _manifest_filespec: str

    def setUp(self):
        """test-level setup."""
        super().setUp()
        self._here = None
        self._broker = None
        self._request = None
        self._loader = None
        self._manifest_filespec = None

    def tearDown(self):
        self._here = None
        self._broker = None
        self._request = None
        self._loader = None
        self._manifest_filespec = None
        super().tearDown()

    @property
    def here(self) -> str:
        """Return the directory path of this test file."""
        if not self._here:
            raise NotImplementedError("Subclasses must set _here")
        return self._here

    @property
    def manifest_filespec(self) -> str:
        """Return the manifest file path for this test."""
        if not self._manifest_filespec:
            raise NotImplementedError("Subclasses must set _manifest_filespec")
        return self._manifest_filespec

    @property
    def SAMBrokerClass(self) -> Type[AbstractBroker]:
        """Return the broker class for this test."""
        if not self._broker_class:
            raise NotImplementedError("Subclasses must set _broker_class")
        return self._broker_class

    @property
    def loader(self) -> SAMLoader:
        """Return the SAMLoader for this test."""
        if self._loader:
            return self._loader

        self._loader = SAMLoader(file_path=self.manifest_filespec)
        if not self._loader.ready:
            raise RuntimeError("Loader is not ready in TestSmarterUserBroker setUpClass")

        self.assertIsInstance(self._loader, SAMLoader)
        json.loads(json.dumps(self._loader.json_data))  # should not raise an exception
        yaml.safe_load(yaml.dump(self._loader.yaml_data))  # should not raise an exception
        logger.info(
            "%s.loader Loaded SAM manifest for testing from %s", self.formatted_class_name, self.manifest_filespec
        )
        return self._loader

    @property
    def request(self) -> HttpRequest:
        """
        Return a basic authenticated HttpRequest with a
        valid SAMUser yaml manifest in the body.
        Ensures user.is_authenticated is True.
        """
        if self._request:
            return self._request

        self._request = HttpRequest()
        self._request.user = self.admin_user

        # Ensure user.is_authenticated is True (for mock users)
        if not getattr(self._request.user, "is_authenticated", True):
            logger.warning(
                "%s.request() Request user is not authenticated; setting is_authenticated to True",
                self.formatted_class_name,
            )
            self._request.user.is_authenticated = lambda: True
        self.assertTrue(self._request.user.is_authenticated)

        # add a SAM manifest to the body
        yaml_data = self.loader.yaml_data
        if isinstance(yaml_data, str):
            yaml_data = yaml_data.encode("utf-8")
        # pylint: disable=protected-access
        self._request._body = yaml_data

        self.assertIsInstance(self._request, HttpRequest)
        logger.info(
            "%s.request() Created HttpRequest for testing with SAM manifest in body from %s",
            self.formatted_class_name,
            self.manifest_filespec,
        )
        return self._request

    @property
    def broker(self) -> AbstractBroker:
        """
        Return the SAMBroker for this test based
        on a default initialization scenario using
        a request object containing a valid SAM manifest in the body
        and a loader initialized with the same manifest.
        """
        if not self._broker:
            self._broker = self.SAMBrokerClass(
                request=self.request,
                loader=self.loader,
            )
        return self._broker

    def get_data_full_filepath(self, filename: str) -> str:
        """
        Return the full file path for a data file in the 'data' subdirectory.

        :param filename: The name of the data file.
        :return: The full file path as a string.
        """
        return os.path.join(self.here, "data", filename)

    def ready(self) -> bool:
        """Return True if the broker is ready."""
        if self._here is None:
            raise RuntimeError("Here not initialized in ready() check.")
        if self._manifest_filespec is None:
            raise RuntimeError("Manifest filespec not initialized in ready() check.")
        if self.loader is None:
            raise RuntimeError("Loader not initialized in ready() check.")
        if self.request is None:
            raise RuntimeError("Request not initialized in ready() check.")
        if self.broker is None:
            raise RuntimeError("Broker not initialized in ready() check.")
        return True
