"""
Test :mod:`smarter.apps.api.utils`: apply_manifest(), which applies a manifest with its kind's broker, in this process.

No request is made: an earlier apply_manifest() posted to the platform's own cli api, and is gone (issue #1082).
"""

import os
from unittest.mock import MagicMock, patch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api import utils
from smarter.apps.api.v1.cli.views.base import APIV1CLIViewError
from smarter.apps.guardrail.models import Guardrail
from smarter.common.exceptions import SmarterValueError

HERE = os.path.abspath(os.path.dirname(__file__))
GUARDRAIL_MANIFEST = os.path.join(
    HERE, "..", "..", "guardrail", "manifest", "brokers", "tests", "data", "guardrail.yaml"
)
GUARDRAIL_APPLY = "smarter.apps.guardrail.manifest.brokers.guardrail.SAMGuardrailBroker.apply"
SECRET_APPLY = "smarter.apps.secret.manifest.brokers.secret.SAMSecretBroker.apply"


def manifest(name: str) -> str:
    with open(GUARDRAIL_MANIFEST, encoding="utf-8") as f:
        return f.read().replace("name: test_guardrail", f"name: {name}")


class TestApplyManifest(TestAccountMixin):
    """Test apply_manifest()."""

    def setUp(self):
        super().setUp()
        self.name = "test_api_utils_guardrail"
        self.addCleanup(Guardrail.objects.filter(name=self.name).delete)

    def test_invalid_arguments(self):
        """Test a missing manifest and file, and a missing or unknown user."""
        with self.assertRaises(SmarterValueError):
            utils.apply_manifest(username=self.admin_user.username)
        with self.assertRaises(SmarterValueError):
            utils.apply_manifest(filespec="/not/a/file.yaml", username=self.admin_user.username)
        self.assertFalse(utils.apply_manifest(manifest=manifest(self.name), username=" "))
        self.assertFalse(utils.apply_manifest(manifest=manifest(self.name), username="not_a_user"))

    def test_apply_manifest(self):
        """Test that the manifest is applied with its kind's broker, from text or a file."""
        self.assertTrue(
            utils.apply_manifest(manifest=manifest(self.name), username=self.admin_user.username, verbose=True)
        )
        self.assertTrue(Guardrail.objects.filter(name=self.name, user_profile=self.user_profile).exists())
        self.assertTrue(utils.apply_manifest(filespec=GUARDRAIL_MANIFEST, username=self.admin_user.username))
        Guardrail.objects.filter(name="test_guardrail", user_profile=self.user_profile).delete()

    def test_makes_no_request(self):
        """Test that applying makes no HTTP request: the module has no HTTP client (issue #1082)."""
        self.assertFalse(hasattr(utils, "httpx"))
        self.assertFalse(hasattr(utils, "apply_manifest_v2"))

    def test_unknown_kind(self):
        self.assertFalse(
            utils.apply_manifest(
                manifest=manifest(self.name).replace("kind: Guardrail", "kind: NotAKind"),
                username=self.admin_user.username,
            )
        )

    def test_failure(self):
        with patch(GUARDRAIL_APPLY, return_value=MagicMock(status_code=400, content=b"bad")):
            with self.assertRaises(Exception):
                utils.apply_manifest(manifest=manifest(self.name), username=self.admin_user.username)
        with patch(GUARDRAIL_APPLY, return_value=None):
            self.assertFalse(utils.apply_manifest(manifest=manifest(self.name), username=self.admin_user.username))
        self.assertTrue(issubclass(APIV1CLIViewError, Exception))

    def test_loggable_manifest(self):
        """A Secret manifest is never logged, and other manifests are logged as they are."""
        secret = "apiVersion: smarter.sh/v1\nkind: Secret\nmetadata:\n  name: openai\nspec:\n  config:\n    value: sk-test-value\n"
        self.assertNotIn("sk-test-value", utils.loggable_manifest(secret) or "")
        self.assertIn("openai", utils.loggable_manifest(secret) or "")
        guardrail = manifest(self.name)
        self.assertEqual(utils.loggable_manifest(guardrail), guardrail)
        self.assertIsNone(utils.loggable_manifest(None))
        self.assertNotIn("sk-test-value", utils.loggable_manifest("{value: [sk-test-value") or "")
        # a failed apply of a Secret, verbose, logs neither the manifest's value nor puts it in the error.
        with (
            patch.object(utils, "logger") as logger,
            patch(SECRET_APPLY, return_value=MagicMock(status_code=400, content=b"bad")),
        ):
            with self.assertRaises(Exception) as raised:
                utils.apply_manifest(manifest=secret, username=self.admin_user.username, verbose=True)
        self.assertNotIn("sk-test-value", str(logger.mock_calls))
        self.assertNotIn("sk-test-value", str(raised.exception))
