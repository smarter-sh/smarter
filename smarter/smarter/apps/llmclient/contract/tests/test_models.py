"""Test :mod:`smarter.apps.llmclient.contract.models`."""

import json
from typing import get_args

from pydantic import ValidationError

from smarter.apps.account.serializers import user_can_delete
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.guardrail.manifest.models.guardrail.const import (
    MANIFEST_KIND as GUARDRAIL_KIND,
)
from smarter.apps.llmclient.contract.models import (
    LLMClientApiCustomDomain,
    LLMClientApiDnsVerificationStatus,
    LLMClientApiExtension,
    LLMClientApiKey,
    LLMClientApiLLMClient,
    LLMClientApiPlugin,
    LLMClientApiTlsCertificateIssuanceStatus,
    LLMClientApiToolKind,
    LLMClientApiVerificationStatus,
)
from smarter.apps.llmclient.models import (
    LLMClient,
    LLMClientAPIKey,
    LLMClientCustomDomain,
    LLMClientExtensions,
    LLMClientPlugin,
)
from smarter.apps.llmclient.serializers import (
    LLMClientAPIKeySerializer,
    LLMClientCustomDomainSerializer,
    LLMClientExtensionsSerializer,
    LLMClientPluginSerializer,
    LLMClientSerializer,
)
from smarter.apps.llmtool.manifest.models.common.plugin.const import (
    MANIFEST_KIND as PLUGIN_KIND,
)
from smarter.apps.llmtool.models import Extension, PluginMeta
from smarter.apps.mcpclient.manifest.models.mcpclient.const import (
    MANIFEST_KIND as MCPCLIENT_KIND,
)
from smarter.lib.drf.models import SmarterAuthToken

NAME = "test_llmclient_contract_models"


def serialized(serializer) -> dict:
    """A serializer's output, as the JSON that the api returned."""
    return json.loads(json.dumps(serializer.data, default=str))


def choices(model, field: str) -> list[str]:
    """The values of a model field's choices."""
    return [value for value, _ in model._meta.get_field(field).choices]


class TestLLMClientContractModels(TestAccountMixin):
    """Test the LLMClient contract's models against the serializers whose output they replace."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(name=NAME, user_profile=self.user_profile)
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        self.llmclient.tags.add("contract")
        extension = Extension.objects.create(slug="contract-models", display_name="Contract Models")
        self.addCleanup(Extension.objects.filter(pk=extension.pk).delete)
        self.extension = LLMClientExtensions.objects.create(llmclient=self.llmclient, extension=extension)
        plugin_meta = PluginMeta.objects.create(name=NAME, user_profile=self.user_profile, plugin_class="static")
        self.addCleanup(PluginMeta.objects.filter(pk=plugin_meta.pk).delete)
        self.plugin = LLMClientPlugin.objects.create(llmclient=self.llmclient, plugin_meta=plugin_meta)
        token, _ = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user_profile=self.user_profile, name=NAME, user=self.admin_user, description=NAME
        )
        self.addCleanup(SmarterAuthToken.objects.filter(pk=token.pk).delete)
        self.api_key = LLMClientAPIKey.objects.create(llmclient=self.llmclient, api_key=token)

    def assert_is_serializers_output(self, model, serializer, *ignore: str):
        """The model's JSON is the serializer's, but for the ignored keys."""
        new = model.model_dump(mode="json")
        old = serialized(serializer)
        for key in ignore:
            new.pop(key)
            old.pop(key)
        differences = sorted(key for key in new.keys() | old.keys() if new.get(key) != old.get(key))
        self.assertEqual(
            new,
            old,
            f"{type(model).__name__} and {type(serializer).__name__} differ in {differences}. "
            f"When the serializer changes, change the contract model in "
            f"smarter/smarter/apps/llmclient/contract/models.py to match, then run `make api-contract` "
            f"to regenerate smarter/smarter/apps/api/v1/contract/openapi.json, and commit both.",
        )

    def test_choices(self):
        """The Literals are the model fields' choices."""
        cases = [
            (LLMClientApiDnsVerificationStatus, LLMClient, "dns_verification_status"),
            (LLMClientApiTlsCertificateIssuanceStatus, LLMClient, "tls_certificate_issuance_status"),
            (LLMClientApiVerificationStatus, LLMClientCustomDomain, "verification_status"),
        ]
        for literal, model, field in cases:
            with self.subTest(field=f"{model.__name__}.{field}"):
                self.assertEqual(list(get_args(literal)), choices(model, field))

    def test_tool_kinds(self):
        """A tool's kind is Extension, or the manifest kind of a plugin, MCPClient or guardrail."""
        self.assertEqual(
            list(get_args(LLMClientApiToolKind)), ["Extension", PLUGIN_KIND, MCPCLIENT_KIND, GUARDRAIL_KIND]
        )

    def test_llmclient_is_the_serializers_output(self):
        """The LLMClient's JSON is the serializer's.

        defaultSystemRole has the time, which changes between the calls.
        """
        model = LLMClientApiLLMClient.from_model(self.llmclient)
        self.assert_is_serializers_output(model, LLMClientSerializer(self.llmclient), "defaultSystemRole")
        self.assertEqual([extension.name for extension in model.extensions], ["contract-models"])
        self.assertEqual([plugin.name for plugin in model.plugins], [NAME])
        self.assertEqual(model.mcpclients, [])
        self.assertEqual(model.guardrails, [])
        self.assertEqual(
            [(tool.id, tool.name, tool.kind) for tool in model.tools],
            [(self.extension.pk, "contract-models", "Extension"), (self.plugin.pk, NAME, PLUGIN_KIND)],
        )
        self.assertEqual([api_key.id for api_key in model.api_keys], [self.api_key.pk])
        self.assertEqual(model.custom_domains, [])
        self.assertEqual(model.tags, ["contract"])

    def test_can_delete_is_the_users(self):
        """CanDelete is the requesting user's, and false without one, as the serializer's always was."""
        self.assertIs(LLMClientApiLLMClient.from_model(self.llmclient).can_delete, False)
        self.assertEqual(
            LLMClientApiLLMClient.from_model(self.llmclient, self.admin_user).can_delete,
            user_can_delete(self.llmclient, "LLMClient", self.admin_user),
        )
        self.assertIs(LLMClientApiLLMClient.from_model(self.llmclient, self.non_admin_user).can_delete, False)

    def test_related_rows_are_the_serializers_output(self):
        self.assert_is_serializers_output(
            LLMClientApiExtension.from_model(self.extension), LLMClientExtensionsSerializer(self.extension)
        )
        self.assert_is_serializers_output(
            LLMClientApiPlugin.from_model(self.plugin), LLMClientPluginSerializer(self.plugin)
        )
        self.assert_is_serializers_output(
            LLMClientApiKey.from_model(self.api_key), LLMClientAPIKeySerializer(self.api_key)
        )

    def test_custom_domain_is_the_serializers_output(self):
        """An unsaved custom domain: saving one would reach DNS."""
        custom_domain = LLMClientCustomDomain(
            id=999999,
            name="example_com",
            user_profile=self.user_profile,
            aws_hosted_zone_id="",
            domain_name="example.com",
            verification_status="Not Verified",
            verification_message="",
        )
        self.assert_is_serializers_output(
            LLMClientApiCustomDomain.from_model(custom_domain), LLMClientCustomDomainSerializer(custom_domain)
        )

    def test_extra_fields_are_forbidden(self):
        data = LLMClientApiExtension.from_model(self.extension).model_dump(mode="json")
        self.assertEqual(LLMClientApiExtension.model_validate(data).name, "contract-models")
        with self.assertRaises(ValidationError):
            LLMClientApiExtension.model_validate({**data, "secret": "x"})
