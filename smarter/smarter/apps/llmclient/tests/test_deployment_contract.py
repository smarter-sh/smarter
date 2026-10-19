"""Tests of smarter.apps.llmclient.views.deployment_contract: the LLMClient deployment page's models and schema."""

import io
import json

from django.core.management import call_command

from smarter.apps.llmclient.views.deployment_contract import (
    SCHEMA_PATH,
    AttachApiKeyRequest,
    CreateApiKeyRequest,
    DeploymentLLMClient,
    contract_schema,
    contract_schema_json,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestLLMClientDeploymentContract(SmarterTestBase):
    """Test the contract's JSON, and that its committed schema is current."""

    def test_schema_is_current(self):
        """The committed schema is the models' schema."""
        self.assertEqual(
            json.loads(SCHEMA_PATH.read_text(encoding="utf-8")),
            contract_schema(),
            "llmclient-deployment.schema.json is out of date. Run `make llmclient-deployment-contract`, and commit it.",
        )
        self.assertEqual(contract_schema_json(), SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_json_is_camel_case(self):
        """The JSON is camelCase, and requests are validated by either name."""
        self.assertIn("workbenchUrl", DeploymentLLMClient.model_json_schema(mode="serialization")["properties"])
        request = AttachApiKeyRequest.model_validate({"keyId": "6f1d2c3b-4a5e-4f60-8172-839405a6b7c8"})
        self.assertEqual(str(request.key_id), "6f1d2c3b-4a5e-4f60-8172-839405a6b7c8")
        request = CreateApiKeyRequest.model_validate({"name": "my_site_chat"})
        self.assertEqual((request.description, request.attach), ("", False))

    def test_export_command(self):
        """The export command writes the schema."""
        output = io.StringIO()
        call_command("export_llmclient_deployment_schema", stdout=output)
        self.assertIn("llmclient-deployment.schema.json", output.getvalue())
