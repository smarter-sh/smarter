"""Test Api v1 CLI reources endpoint."""

from http import HTTPStatus

from rest_framework.test import APIClient

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

    def validate_response(self, response: dict) -> None:

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

    def test_resources_only_prompt_is_deployable(self) -> None:
        """Test that Prompt is the only resource kind flagged as deployable."""
        response, status = self.get_response(path=self.path)
        self.assertEqual(status, HTTPStatus.OK)
        data = response[SmarterJournalApiResponseKeys.DATA]

        deployable_singulars = [resource["Singular"] for resource in data if resource["Deployable"]]
        self.assertEqual(deployable_singulars, [SAMKinds.PROMPT.value])

        not_deployable_singulars = [resource["Singular"] for resource in data if not resource["Deployable"]]
        self.assertNotIn(SAMKinds.PROMPT.value, not_deployable_singulars)

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
                "Deployable": True,
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
                "Deployable": False,
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
