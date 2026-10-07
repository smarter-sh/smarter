"""
Test that /api/v1/cli/apply/ returns an intelligible error, with a status that matches it, for invalid LLMClient manifests.

The cases are in data/llmclient-apply-errors.yaml. Each changes the valid manifest in
data/llmclient-apply-errors-base.yaml in one way, e.g. a temperature that is out of range.
"""

import copy
import os
from http import HTTPStatus
from typing import Any

import yaml

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.cli.views.swagger import BUG_REPORT
from smarter.apps.llmclient.models import LLMClient
from smarter.lib.django.shortcuts import reverse
from smarter.lib.journal.enum import (
    SmarterJournalApiResponseErrorKeys,
    SmarterJournalApiResponseKeys,
)

from .base_class import ApiV1CliTestBase

HERE = os.path.dirname(os.path.abspath(__file__))
BASE_MANIFEST = os.path.join(HERE, "data", "llmclient-apply-errors-base.yaml")
CASES = os.path.join(HERE, "data", "llmclient-apply-errors.yaml")


def load_yaml(path: str) -> Any:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def mutated(manifest: dict, case: dict) -> dict:
    """The manifest, changed as the case says."""
    keys = case["path"].split(".")
    node = manifest
    for key in keys[:-1]:
        node = node[key]
    if case.get("delete"):
        node.pop(keys[-1], None)
    else:
        node[keys[-1]] = case["value"] * case["repeat"] if "repeat" in case else case["value"]
    return manifest


class TestApiCliV1LLMClientApplyErrors(ApiV1CliTestBase):
    """Test the status and the description of the response to applying each invalid LLMClient manifest."""

    def setUp(self):
        super().setUp()
        self.path = reverse(self.namespace + ApiV1CliReverseViews.apply)
        self.base_manifest = load_yaml(BASE_MANIFEST)
        self.base_manifest["metadata"]["name"] = self.name
        self.addCleanup(LLMClient.objects.filter(user_profile=self.user_profile, name=self.name).delete)

    def apply(self, body: str) -> tuple[dict, int]:
        return self.get_response(path=self.path, manifest=body)

    def test_valid_manifest(self):
        """Test that the base manifest, which every case changes, is valid."""
        response, status = self.apply(yaml.safe_dump(self.base_manifest))
        self.assertEqual(status, HTTPStatus.OK, response)

    def test_invalid_manifests(self):
        """Test that each invalid manifest is a client error, whose description says what is wrong."""
        response, status = self.apply(yaml.safe_dump(self.base_manifest))
        self.assertEqual(status, HTTPStatus.OK, response)
        for case in load_yaml(CASES):
            with self.subTest(case=case["name"]):
                if "body" in case:
                    body = case["body"]
                else:
                    body = yaml.safe_dump(mutated(copy.deepcopy(self.base_manifest), case))
                response, status = self.apply(body)
                self.assertEqual(status, case["status"], response)
                error = response.get(SmarterJournalApiResponseKeys.ERROR)
                self.assertIsInstance(error, dict, response)
                description = error.get(SmarterJournalApiResponseErrorKeys.DESCRIPTION)
                self.assertIsInstance(description, str, response)
                self.assertNotIn(BUG_REPORT, description)
                for expected in case["expect"]:
                    self.assertIn(expected, description)

        # a manifest that fails validation changes nothing
        llmclient = LLMClient.objects.get(user_profile=self.user_profile, name=self.name)
        self.assertEqual(llmclient.default_temperature, self.base_manifest["spec"]["config"]["defaultTemperature"])
        self.assertEqual(llmclient.provider, self.base_manifest["spec"]["config"]["provider"])
        self.assertEqual(llmclient.app_name, self.base_manifest["spec"]["config"]["appName"])

    def test_name_that_is_not_snake_case(self):
        """Test that a name is stored in snake_case, and that applying the manifest again updates it."""
        name = f"Apply Error Test {self.hash_suffix}!"
        stored_name = f"apply_error_test_{self.hash_suffix}"
        self.addCleanup(LLMClient.objects.filter(user_profile=self.user_profile, name=stored_name).delete)
        manifest = copy.deepcopy(self.base_manifest)
        manifest["metadata"]["name"] = name
        for description in ("first", "second"):
            manifest["metadata"]["description"] = description
            response, status = self.apply(yaml.safe_dump(manifest))
            self.assertEqual(status, HTTPStatus.OK, response)
        llmclient = LLMClient.objects.get(user_profile=self.user_profile, name=stored_name)
        self.assertEqual(llmclient.description, "second")
