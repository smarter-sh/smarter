"""
Test :mod:`smarter.apps.api.utils`: apply_manifest(), over the cli api, and apply_manifest_v2(), with a broker.

apply_manifest()'s http request is never sent: httpx.post is patched.
"""

import os
from unittest.mock import MagicMock, patch

import httpx

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api import utils
from smarter.apps.api.v1.cli.views.base import APIV1CLIViewError
from smarter.apps.guardrail.models import Guardrail
from smarter.common.exceptions import SmarterValueError
from smarter.lib.drf.models import SmarterAuthToken

HERE = os.path.abspath(os.path.dirname(__file__))
GUARDRAIL_MANIFEST = os.path.join(
    HERE, "..", "..", "guardrail", "manifest", "brokers", "tests", "data", "guardrail.yaml"
)


def manifest(name: str) -> str:
    with open(GUARDRAIL_MANIFEST, encoding="utf-8") as f:
        return f.read().replace("name: test_guardrail", f"name: {name}")


class TestApplyManifest(TestAccountMixin):
    """Test apply_manifest() and apply_manifest_v2()."""

    def setUp(self):
        super().setUp()
        self.name = "test_api_utils_guardrail"
        self.addCleanup(Guardrail.objects.filter(name=self.name).delete)

    def response(self, status_code, content=b'{"ok": true}'):
        return MagicMock(status_code=status_code, content=content)

    def test_apply_manifest(self):
        """Test that the manifest is posted with a single-use api key, which is then deleted."""
        with patch(f"{utils.__name__}.httpx.post", return_value=self.response(httpx.codes.OK)) as post:
            self.assertTrue(utils.apply_manifest(manifest=manifest(self.name), username=self.admin_user.username))
            self.assertTrue(
                utils.apply_manifest(filespec=GUARDRAIL_MANIFEST, username=self.admin_user.username, verbose=True)
            )
        self.assertTrue(post.call_args.kwargs["headers"]["Authorization"].startswith("Token "))
        self.assertFalse(SmarterAuthToken.objects.filter(name="apply_manifest").exists())

    def test_apply_manifest_failure(self):
        with patch(f"{utils.__name__}.httpx.post", return_value=self.response(httpx.codes.BAD_REQUEST)):
            self.assertFalse(utils.apply_manifest(manifest=manifest(self.name), username=self.admin_user.username))

    def test_apply_manifest_undecodable_response(self):
        with patch(f"{utils.__name__}.httpx.post", return_value=self.response(httpx.codes.OK, b"not json")):
            self.assertTrue(utils.apply_manifest(manifest=manifest(self.name), username=self.admin_user.username))

    def test_invalid_arguments(self):
        """Test a missing manifest and file, and a missing or unknown user, for both versions."""
        for function in (utils.apply_manifest, utils.apply_manifest_v2):
            with self.subTest(function=function.__name__):
                with self.assertRaises(SmarterValueError):
                    function(username=self.admin_user.username)
                with self.assertRaises(SmarterValueError):
                    function(filespec="/not/a/file.yaml", username=self.admin_user.username)
                self.assertFalse(function(manifest=manifest(self.name), username=" "))
                self.assertFalse(function(manifest=manifest(self.name), username="not_a_user"))

    def test_apply_manifest_v2(self):
        """Test that the manifest is applied with its kind's broker."""
        self.assertTrue(
            utils.apply_manifest_v2(manifest=manifest(self.name), username=self.admin_user.username, verbose=True)
        )
        self.assertTrue(Guardrail.objects.filter(name=self.name, user_profile=self.user_profile).exists())
        self.assertTrue(
            utils.apply_manifest_v2(
                filespec=GUARDRAIL_MANIFEST.replace("guardrail.yaml", "guardrail.yaml"),
                username=self.admin_user.username,
            )
        )
        Guardrail.objects.filter(name="test_guardrail", user_profile=self.user_profile).delete()

    def test_apply_manifest_v2_unknown_kind(self):
        self.assertFalse(
            utils.apply_manifest_v2(
                manifest=manifest(self.name).replace("kind: Guardrail", "kind: NotAKind"),
                username=self.admin_user.username,
            )
        )

    def test_apply_manifest_v2_failure(self):
        with patch(
            "smarter.apps.guardrail.manifest.brokers.guardrail.SAMGuardrailBroker.apply",
            return_value=MagicMock(status_code=400, content=b"bad"),
        ):
            with self.assertRaises(Exception):
                utils.apply_manifest_v2(manifest=manifest(self.name), username=self.admin_user.username)
        with patch("smarter.apps.guardrail.manifest.brokers.guardrail.SAMGuardrailBroker.apply", return_value=None):
            self.assertFalse(utils.apply_manifest_v2(manifest=manifest(self.name), username=self.admin_user.username))
        self.assertTrue(issubclass(APIV1CLIViewError, Exception))
