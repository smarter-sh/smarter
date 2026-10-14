"""Test Api v1 CLI reources endpoint."""

from http import HTTPStatus
from unittest import mock

from rest_framework.test import APIClient

from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.apps.api.v1.cli.tests.base_class import ApiV1CliTestBase
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.api import SmarterApiVersions
from smarter.lib import json, logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import (
    SCLIResponseMetadata,
    SmarterJournalApiResponseKeys,
)
from smarter.lib.typing import SmarterDictType

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.API_LOGGING])
logger_prefix = logging.formatted_text(f"{__name__}.TestApiCliV1Resources")

# the exact keys that every resource dict returned by ApiV1CliResourcesApiView.dictionaryize()
# is expected to contain.
RESOURCE_DICT_KEYS = {"Singular", "Plural", "APIKind", "Display", "DisplayPlural", "Deployable"}


class TestApiCliV1Resources(ApiV1CliTestBase):
    """
    Test Api v1 CLI resources endpoint.

    This class inherits ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, account, user_profile and token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    Account.
    """

    def setUp(self):
        super().setUp()
        self.name = self.account.name
        self.path = reverse(self.namespace + ApiV1CliReverseViews.resources, kwargs=None)

    def validate_response(self, response: SmarterDictType) -> None:

        logger.debug("validate_response(): %s", json.dumps(response))

        # validate the response and status are both good
        self.assertIsInstance(response, dict)

        # validate the structure of the response
        self.assertIn(SmarterJournalApiResponseKeys.API, response.keys())
        self.assertIn(SmarterJournalApiResponseKeys.DATA, response.keys())
        self.assertIn(SmarterJournalApiResponseKeys.METADATA, response.keys())

        # validate the metadata
        self.assertEqual(response[SmarterJournalApiResponseKeys.API], SmarterApiVersions.V1)
        metadata = response[SmarterJournalApiResponseKeys.METADATA]
        self.assertIsInstance(metadata, dict)
        self.assertIn(SCLIResponseMetadata.COMMAND, metadata.keys())

        # validate the payload
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.DATA], list)

    def test_resources(self) -> None:
        """Test that the resources command returns a 200 response with a well-formed envelope."""
        response, status = self.get_response(path=self.path)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)

    def test_resources_count_matches_sam_kinds(self) -> None:
        """Test that the resources command returns exactly one entry per SAMKinds member."""
        response, status = self.get_response(path=self.path)
        self.assertEqual(status, HTTPStatus.OK)
        data = response[SmarterJournalApiResponseKeys.DATA]
        all_kinds = SAMKinds.all()
        self.assertEqual(len(data), len(all_kinds))

    def test_resources_entries_have_required_keys(self) -> None:
        """Test that every resource entry contains exactly the expected keys, with correctly typed values."""
        response, status = self.get_response(path=self.path)
        self.assertEqual(status, HTTPStatus.OK)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.assertGreater(len(data), 0)
        for resource in data:
            self.assertEqual(set(resource.keys()), RESOURCE_DICT_KEYS)
            self.assertIsInstance(resource["Singular"], str)
            self.assertIsInstance(resource["Plural"], str)
            self.assertIsInstance(resource["APIKind"], str)
            self.assertIsInstance(resource["Display"], str)
            self.assertIsInstance(resource["DisplayPlural"], str)
            self.assertIsInstance(resource["Deployable"], bool)

    def test_resources_apikind_and_display_mirror_singular(self) -> None:
        """Test that APIKind and Display mirror Singular, and DisplayPlural mirrors Plural, for every entry."""
        response, status = self.get_response(path=self.path)
        self.assertEqual(status, HTTPStatus.OK)
        data = response[SmarterJournalApiResponseKeys.DATA]
        for resource in data:
            self.assertEqual(resource["APIKind"], resource["Singular"])
            self.assertEqual(resource["Display"], resource["Singular"])
            self.assertEqual(resource["DisplayPlural"], resource["Plural"])

    def test_resources_deployable_is_the_brokers(self) -> None:
        """Test that a kind is deployable exactly when its broker is, and that Prompt, whose broker doesn't deploy, isn't."""
        response, status = self.get_response(path=self.path)
        self.assertEqual(status, HTTPStatus.OK)
        data = response[SmarterJournalApiResponseKeys.DATA]

        for resource in data:
            with self.subTest(kind=resource["APIKind"]):
                self.assertEqual(resource["Deployable"], Brokers.get_broker(resource["APIKind"]).deployable)

        deployable = sorted(resource["Singular"] for resource in data if resource["Deployable"])
        self.assertIn(SAMKinds.LLM_CLIENT.value, deployable)
        self.assertNotIn(SAMKinds.PROMPT.value, deployable)

    def test_resources_known_entries(self) -> None:
        """Spot-check a handful of well-known resource kinds, including a pluralization edge case."""
        response, status = self.get_response(path=self.path)
        self.assertEqual(status, HTTPStatus.OK)
        data = response[SmarterJournalApiResponseKeys.DATA]
        by_singular = {resource["Singular"]: resource for resource in data}

        self.assertEqual(
            by_singular[SAMKinds.PROMPT.value],
            {
                "Singular": "Prompt",
                "Plural": "Prompts",
                "APIKind": "Prompt",
                "Display": "Prompt",
                "DisplayPlural": "Prompts",
                "Deployable": False,
            },
        )
        self.assertEqual(
            by_singular[SAMKinds.SQL_CONNECTION.value],
            {
                "Singular": "SqlConnection",
                "Plural": "SqlConnections",
                "APIKind": "SqlConnection",
                "Display": "SqlConnection",
                "DisplayPlural": "SqlConnections",
                "Deployable": False,
            },
        )
        self.assertEqual(
            by_singular[SAMKinds.AUTH_TOKEN.value],
            {
                "Singular": "SmarterAuthToken",
                "Plural": "SmarterAuthTokens",
                "APIKind": "SmarterAuthToken",
                "Display": "SmarterAuthToken",
                "DisplayPlural": "SmarterAuthTokens",
                "Deployable": True,
            },
        )
        # Vectorsearch is an irregular plural ("-search" -> "-searches"), so it's a good
        # canary for regressions in the underlying pluralization logic.
        self.assertEqual(by_singular[SAMKinds.VECTORSEARCH.value]["Plural"], "Vectorsearches")

    def test_resources_no_query_params_required(self) -> None:
        """Test that the resources command does not require a manifest body or query params."""
        response, status = self.get_response(path=self.path, data=None, manifest=None)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)

    def test_resources_requires_authentication(self) -> None:
        """Test that an unauthenticated request to the resources endpoint is rejected."""
        client = APIClient()
        response = client.post(path=self.path, data=None, content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_resources_get_not_allowed(self) -> None:
        """Test that GET is not an allowed method on the resources endpoint."""
        client = APIClient()
        headers = {"Authorization": f"Token {self.token_key}"}
        response = client.get(path=self.path, headers=headers)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def assert_journaled_error(self, response: SmarterDictType, status: int, error_class: str, command: str) -> None:
        """Assert that an error response is the journal's error envelope, not a bare {"error": "..."}."""
        self.assertEqual(response[SmarterJournalApiResponseKeys.API], SmarterApiVersions.V1)
        self.assertEqual(response[SmarterJournalApiResponseKeys.METADATA]["command"], command)
        error = response["error"]
        self.assertIsInstance(error, dict)
        self.assertEqual(error["errorClass"], error_class)
        self.assertEqual(error["status"], status)

    def test_resources_error_is_journaled(self) -> None:
        """An error is returned as a journaled error response, with its status."""
        path = reverse(self.namespace + ApiV1CliReverseViews.resources, kwargs=None)
        with mock.patch(
            "smarter.apps.api.v1.cli.views.nonbrokered.resources.ApiV1CliResourcesApiView.dictionaryize",
            side_effect=RuntimeError("broken"),
        ):
            response, status = self.get_response(path=path)
        self.assertEqual(status, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assert_journaled_error(response, HTTPStatus.INTERNAL_SERVER_ERROR, "RuntimeError", "resources")
