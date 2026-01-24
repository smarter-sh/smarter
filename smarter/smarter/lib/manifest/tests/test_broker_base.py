# pylint: disable=wrong-import-position
"""Base class for testing classes derived from AbstractBroker."""

import logging
import os
from http import HTTPStatus
from typing import Type

import yaml
from django.http import HttpRequest

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.utils import mask_string
from smarter.lib import json
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
)
from smarter.lib.manifest.loader import SAMLoader

HERE = os.path.abspath(os.path.dirname(__file__))
logger = logging.getLogger(__name__)
logger_prefix = formatted_text(f"{HERE}.TestSAMBrokerBaseClass()")


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
    test_sam_broker_base_logger_prefix = formatted_text(f"{__name__}.TestSAMBrokerBaseClass()")

    @classmethod
    def setUpClass(cls):
        """class-level setup."""
        super().setUpClass()
        cls.token_record, cls.token_key = SmarterAuthToken.objects.create(
            user_profile=cls.user_profile,
            name="testAPIKey",
            user=cls.admin_user,
            description="Test API Key",
            is_active=True,
        )  # type: ignore
        logger.debug(
            "%s.setUpClass() Created test API token for user %s - %s",
            logger_prefix,
            cls.admin_user.username,
            mask_string(cls.token_key),
        )

        title = f" {logger_prefix}.setUpClass() "
        msg = "*" * ((cls.line_width - len(title)) // 2) + title + "*" * ((cls.line_width - len(title)) // 2)
        logger.debug(msg)

    @classmethod
    def tearDownClass(cls):
        """class-level teardown."""
        title = f" {logger_prefix}.tearDownClass() "
        msg = "*" * ((cls.line_width - len(title)) // 2) + title + "*" * ((cls.line_width - len(title)) // 2)
        logger.debug(msg)
        try:
            cls.token_record.delete()
        # pylint: disable=broad-except
        except Exception:
            pass
        super().tearDownClass()

    def setUp(self):
        """test-level setup."""
        super().setUp()
        self._here = None
        self._broker = None
        self._request = None
        self._loader = None
        self._manifest_filespec = None
        title = f" {logger_prefix}.{self._testMethodName}() "
        msg = "-" * ((self.line_width - len(title)) // 2) + title + "-" * ((self.line_width - len(title)) // 2)
        logger.debug(msg)

    def tearDown(self):
        title = f" {logger_prefix}.tearDown() {self._testMethodName} "
        msg = "-" * ((self.line_width - len(title)) // 2) + title + "-" * ((self.line_width - len(title)) // 2)
        logger.debug(msg)
        self._here = None
        self._broker = None
        self._request = None
        self._loader = None
        self._manifest_filespec = None
        super().tearDown()

    @property
    def kwargs(self) -> dict:
        """Return default kwargs for broker methods."""
        if not self.ready:
            raise RuntimeError(f"{self.formatted_class_name}.kwargs accessed before ready state")
        return {
            SAMMetadataKeys.NAME.value: self.admin_user.username,
        }

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
        logger.debug(
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
        self._request.headers = {"Authorization": f"Token {self.token_key}"}
        logger.debug("%s.request() Set Authorization header: %s", self.formatted_class_name, self._request.headers)
        # self._request.user = self.admin_user

        # # Ensure user.is_authenticated is True (for mock users)
        # if not getattr(self._request.user, "is_authenticated", True):
        #     logger.warning(
        #         "%s.request() Request user is not authenticated; setting is_authenticated to True",
        #         self.formatted_class_name,
        #     )
        #     self._request.user.is_authenticated = lambda: True
        # self.assertTrue(self._request.user.is_authenticated)

        # add a SAM manifest to the body
        yaml_data = self.loader.yaml_data
        if isinstance(yaml_data, str):
            yaml_data = yaml_data.encode("utf-8")
        # pylint: disable=protected-access
        self._request._body = yaml_data

        self.assertIsInstance(self._request, HttpRequest)
        logger.debug(
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

    @property
    def ready(self) -> bool:
        """Return True if the broker is ready."""
        if not super().ready:
            return False
        if self._here is None:
            raise RuntimeError("Here not initialized in ready() check.")
        if self._manifest_filespec is None:
            raise RuntimeError("Manifest filespec not initialized in ready() check.")
        if self.loader is None:
            raise RuntimeError("Loader not initialized in ready() check.")
        if self.request is None:
            raise RuntimeError("Request not initialized in ready() check.")
        if hasattr(self.request, "user") and self.request.user is None:
            raise RuntimeError("Request user not initialized in ready() check.")
        if (
            hasattr(self.request, "user")
            and hasattr(self.request.user, "is_authenticated")
            and not self.request.user.is_authenticated
        ):
            raise RuntimeError("Request user is not authenticated in ready() check.")
        if self.broker is None:
            raise RuntimeError("Broker not initialized in ready() check.")
        return True

    def get_data_full_filepath(self, filename: str) -> str:
        """
        Return the full file path for a data file in the 'data' subdirectory.

        :param filename: The name of the data file.
        :return: The full file path as a string.
        """
        return os.path.join(self.here, "data", filename)

    def validate_smarter_journaled_json_response_ok(
        self,
        response: SmarterJournaledJsonResponse,
    ) -> bool:
        """
        Validate that the response is a SmarterJournaledJsonResponse.
        Verify that it returns a SmarterJournaledJsonResponse with expected structure:
            {
            "data": {
                "ready": true,
                "url": "http://testserver/unknown/",
                "session_key": "c277c2d892843f3459f8d65924efa23932823f86d4b5e56d33ef2276c095c65f",
                "auth_header": null,
                "api_token": null,
                "data": {
                "apiVersion": "smarter.sh/v1",
                "kind": "User",
                "metadata": {
                    "description": "an example user manifest for the Smarter API User",
                    "name": "example_user",
                    "username": "example_user",
                    "version": "1.0.0",
                    "tags": [],
                    "annotations": []
                },
                "spec": {
                    "config": {
                    "email": "joe@mail.com",
                    "firstName": "John",
                    "isActive": true,
                    "isStaff": false,
                    "lastName": "Doe"
                    }
                }
                },
                "message": "User test_admin_user_90599131136f4e98 applied successfully",
                "api": "smarter.sh/v1",
                "thing": "User",
                "metadata": {
                "command": "apply"
                }
            }
            }

        :param response: The response to validate.
        """

        # Validate that the response is a SmarterJournaledJsonResponse
        self.assertIsInstance(
            response,
            SmarterJournaledJsonResponse,
            msg=f"Response is not a SmarterJournaledJsonResponse. Got: {type(response)}",
        )

        # Validate that the response has HTTP 200 OK status
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsInstance(response.to_json(), dict, msg="Response to_json() is not a dict")

        # Validate that the response content can be
        # properly decoded to a dict
        response_json: dict = json.loads(response.content.decode("utf-8"))
        self.assertIsInstance(response_json, dict)

        return True

    def validate_example_manifest(
        self,
        response: SmarterJournaledJsonResponse,
    ) -> bool:
        """
        Validate that the response is a SmarterJournaledJsonResponse containing
        a properly structured SAM manifest dict.
        """

        # Validate that the response is a properly
        # structured SAM manifest dict
        response_json: dict = json.loads(response.content.decode("utf-8"))
        self.assertIsInstance(response_json, dict)
        data = response_json.get(SCLIResponseGet.DATA.value)
        self.assertIsInstance(data, dict, msg=f"Response data is not a dict. response_json: {response_json}")

        # Validate that the response is a properly
        # structured SAM manifest dict
        self.assertIsNotNone(
            data.get(SAMKeys.APIVERSION.value),
            msg=f"apiVersion missing in manifest dict. response_json: {response_json}",
        )
        self.assertIsNotNone(
            data.get(SAMKeys.KIND.value), msg=f"kind missing in manifest dict. response_json: {response_json}"
        )
        self.assertIsNotNone(
            data.get(SAMKeys.METADATA.value), msg=f"metadata missing in manifest dict. response_json: {response_json}"
        )
        self.assertIsNotNone(
            data.get(SAMKeys.SPEC.value), msg=f"spec missing in manifest dict. response_json: {response_json}"
        )

        return True

    def validate_get(self, response: SmarterJournaledJsonResponse) -> bool:
        """
        Validate that the response is a SmarterJournaledJsonResponse
        containing a properly structured SAM manifest dict.
        """
        response_json: dict = json.loads(response.content.decode("utf-8"))
        self.assertIsInstance(response_json, dict)
        data = response_json.get(SCLIResponseGet.DATA.value)  # type: ignore
        self.assertIsInstance(data, dict, msg=f"Response data is not a dict. response_json: {response_json}")
        data: dict = data.get(SCLIResponseGet.DATA.value)  # type: ignore
        self.assertIsInstance(data, dict, msg=f"Response data.data is not a dict. response_json: {response_json}")

        self.assertIn("titles", data.keys(), msg=f"'titles' missing in manifest dict. response_json: {response_json}")
        self.assertIn("items", data.keys(), msg=f"'items' missing in manifest dict. response_json: {response_json}")

        return True

    def validate_apply(
        self,
        response: SmarterJournaledJsonResponse,
    ) -> bool:
        """
        Validate that the response is a SmarterJournaledJsonResponse
        containing a properly structured SAM manifest dict after an apply operation.
        """

        # Validate that the response is a properly
        # structured SAM manifest dict
        response_json: dict = json.loads(response.content.decode("utf-8"))
        self.assertIsInstance(response_json, dict)
        data = response_json.get(SCLIResponseGet.DATA.value)
        self.assertIsInstance(
            data, dict, msg=f"Response data is not a dict. response_json: {response_json}, data: {data}"
        )
        data = data.get(SCLIResponseGet.DATA.value)
        self.assertIsInstance(
            data, dict, msg=f"Response data.data is not a dict. response_json: {response_json}, data: {data}"
        )

        # Validate that the response is a properly
        # structured SAM manifest dict
        self.assertIsNotNone(
            data.get(SAMKeys.APIVERSION.value),
            msg=f"apiVersion missing in manifest dict. response_json: {response_json}, data: {data}",
        )
        self.assertIsNotNone(
            data.get(SAMKeys.KIND.value),
            msg=f"kind missing in manifest dict. response_json: {response_json}, data: {data}",
        )
        self.assertIsNotNone(
            data.get(SAMKeys.METADATA.value),
            msg=f"metadata missing in manifest dict. response_json: {response_json}, data: {data}",
        )
        self.assertIsNotNone(
            data.get(SAMKeys.SPEC.value),
            msg=f"spec missing in manifest dict. response_json: {response_json}, data: {data}",
        )

        return True
