# pylint: disable=wrong-import-position
"""Test SAMCustomDomainBroker."""

import os
from unittest.mock import patch

from smarter.apps.llmclient.manifest.brokers.custom_domain import (
    SAMCustomDomainBroker,
    SAMCustomDomainBrokerError,
)
from smarter.apps.llmclient.manifest.brokers.llmclient import SAMLLMClientBroker
from smarter.apps.llmclient.manifest.models.custom_domain.model import SAMCustomDomain
from smarter.apps.llmclient.models import (
    LLMClient,
    LLMClientCustomDomain,
    LLMClientCustomDomainDNS,
)
from smarter.lib import json, logging
from smarter.lib.manifest.broker import (
    SAMBrokerError,
    SAMBrokerErrorDependencies,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

logger = logging.getLogger(__name__)

CUSTOM_DOMAIN_NAME = "test_custom_domain"
DOMAIN_NAME = "test-custom-domain-broker.example.com"


class TestSmarterCustomDomainBroker(TestSAMBrokerBaseClass):
    """Test the Smarter SAMCustomDomainBroker."""

    @classmethod
    def tearDownClass(cls):
        LLMClientCustomDomain.objects.filter(user_profile__account=cls.account).delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = self.get_data_full_filepath("custom_domain.yaml")
        self.addCleanup(LLMClientCustomDomain.objects.filter(user_profile=self.user_profile).delete)

    @property
    def SAMBrokerClass(self) -> type[SAMCustomDomainBroker]:
        return SAMCustomDomainBroker

    @property
    def broker(self) -> SAMCustomDomainBroker:
        return super().broker  # type: ignore

    def new_broker(self, manifest: str = "") -> SAMCustomDomainBroker:
        """Return a new broker for the manifest in ./data, or for the given manifest text."""
        if not manifest:
            with open(self.get_data_full_filepath("custom_domain.yaml"), encoding="utf-8") as f:
                manifest = f.read()
        return SAMCustomDomainBroker(request=self.request, loader=SAMLoader(manifest=manifest))

    def custom_domain(self) -> LLMClientCustomDomain:
        return LLMClientCustomDomain.objects.get(user_profile=self.user_profile, name=CUSTOM_DOMAIN_NAME)

    def use_in_llmclient(self, name: str = "test_custom_domain_dependency") -> LLMClient:
        """Return a new LLMClient that uses the CustomDomain."""
        llmclient = LLMClient.objects.create(name=name, user_profile=self.user_profile)
        self.addCleanup(LLMClient.objects.filter(pk=llmclient.pk).delete)
        # update(), rather than save(), which sends llmclient signals.
        LLMClient.objects.filter(pk=llmclient.pk).update(custom_domain=self.custom_domain())
        llmclient.refresh_from_db()
        return llmclient

    def test_broker_initialization(self):
        """Test the broker's kind and model classes, and that it creates nothing lazily."""
        self.assertTrue(self.ready)
        self.assertEqual(self.broker.kind, "CustomDomain")
        self.assertIs(self.broker.ORMModelClass, LLMClientCustomDomain)
        self.assertIsInstance(self.broker.manifest, SAMCustomDomain)
        self.assertIsNone(self.broker.custom_domain)

    def test_example_manifest(self):
        response = self.broker.example_manifest(self.request)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        SAMCustomDomain(**json.loads(response.content)["data"])

    def test_invalid_domain_name(self):
        manifest = (
            "apiVersion: smarter.sh/v1\nkind: CustomDomain\nmetadata:\n  name: bad\n  description: bad\n"
            "  version: 1.0.0\nspec:\n  config:\n    domainName: not a domain\n"
        )
        with self.assertRaises(Exception):
            _ = self.new_broker(manifest).manifest

    def test_apply(self):
        """Apply() creates the CustomDomain, owned by the user."""
        response = self.broker.apply(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        custom_domain = self.custom_domain()
        self.assertEqual(custom_domain.domain_name, DOMAIN_NAME)
        self.assertEqual(custom_domain.description, "A custom domain for unit testing.")
        self.assertEqual(custom_domain.tags_list, ["test"])
        self.assertEqual(
            custom_domain.verification_status, LLMClientCustomDomain.VerificationStatusChoices.NOT_VERIFIED
        )
        self.assertEqual(custom_domain.aws_hosted_zone_id, "")

    def test_apply_updates(self):
        """Apply() updates an existing CustomDomain, including its domain name while it is not registered."""
        self.broker.apply(self.request, **self.kwargs)
        manifest = open(self.get_data_full_filepath("custom_domain.yaml"), encoding="utf-8").read()
        self.new_broker(manifest.replace(DOMAIN_NAME, "renamed-" + DOMAIN_NAME)).apply(self.request, **self.kwargs)
        self.assertEqual(self.custom_domain().domain_name, "renamed-" + DOMAIN_NAME)
        self.assertEqual(LLMClientCustomDomain.objects.filter(user_profile=self.user_profile).count(), 1)

    def test_apply_refuses_to_change_a_registered_domain_name(self):
        self.broker.apply(self.request, **self.kwargs)
        LLMClientCustomDomain.objects.filter(pk=self.custom_domain().pk).update(aws_hosted_zone_id="ZREGISTERED")
        manifest = open(self.get_data_full_filepath("custom_domain.yaml"), encoding="utf-8").read()
        with self.assertRaises(SAMCustomDomainBrokerError):
            self.new_broker(manifest.replace(DOMAIN_NAME, "other.example.com")).apply(self.request, **self.kwargs)
        self.assertEqual(self.custom_domain().domain_name, DOMAIN_NAME)

    def test_describe(self):
        """Describe() returns the manifest, with the hosted zone and DNS records in its status."""
        self.broker.apply(self.request, **self.kwargs)
        custom_domain = self.custom_domain()
        LLMClientCustomDomain.objects.filter(pk=custom_domain.pk).update(aws_hosted_zone_id="ZTEST")
        self.custom_domain().set_verification_status(LLMClientCustomDomain.VerificationStatusChoices.VERIFIED)
        LLMClientCustomDomainDNS.objects.create(
            custom_domain=custom_domain, record_name=DOMAIN_NAME, record_type="NS", record_value="ns-1.aws."
        )
        response = self.new_broker().describe(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        data = json.loads(response.content)["data"]
        SAMCustomDomain(**data)
        self.assertEqual(data["spec"]["config"]["domainName"], DOMAIN_NAME)
        self.assertEqual(data["status"]["awsHostedZoneId"], "ZTEST")
        self.assertEqual(data["status"]["verificationStatus"], "Verified")
        self.assertIsNotNone(data["status"]["verifiedAt"])
        self.assertEqual(data["status"]["dnsRecords"], [f"{DOMAIN_NAME} 600 NS ns-1.aws."])
        self.assertEqual(data["status"]["username"], self.user_profile.user.username)

    def test_describe_not_found(self):
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.broker.describe(self.request, **self.kwargs)

    def test_get(self):
        self.broker.apply(self.request, **self.kwargs)
        response = self.broker.get(self.request)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        items = json.loads(response.content)["data"]["data"]["items"]
        self.assertIn(CUSTOM_DOMAIN_NAME, [item["name"] for item in items])

    def test_delete(self):
        self.broker.apply(self.request, **self.kwargs)
        response = self.new_broker().delete(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertFalse(LLMClientCustomDomain.objects.filter(user_profile=self.user_profile).exists())
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.new_broker().delete(self.request, **self.kwargs)

    def test_dependencies(self):
        """Dependencies() returns a broker for the LLMClient that uses the CustomDomain."""
        self.broker.apply(self.request, **self.kwargs)
        self.assertEqual(self.new_broker().dependencies(), [])
        llmclient = self.use_in_llmclient()
        dependencies = self.new_broker().dependencies()
        self.assertEqual(len(dependencies), 1)
        self.assertIsInstance(dependencies[0], SAMLLMClientBroker)
        self.assertEqual(dependencies[0].name, llmclient.name)

    def test_delete_refused_while_used(self):
        """Delete() refuses to delete a CustomDomain that an LLMClient uses, which would cascade to the LLMClient."""
        self.broker.apply(self.request, **self.kwargs)
        llmclient = self.use_in_llmclient()
        with self.assertRaises(SAMBrokerErrorDependencies) as context:
            self.new_broker().delete(self.request, **self.kwargs)
        self.assertIn(f"LLMClient {llmclient.name}", str(context.exception))
        self.assertTrue(LLMClient.objects.filter(pk=llmclient.pk).exists())
        response = self.new_broker().describe(self.request, **self.kwargs)
        dependencies = json.loads(response.content)["data"]["status"]["dependencies"]
        self.assertEqual(dependencies, [{"kind": "LLMClient", "name": llmclient.name}])

    def test_deploy(self):
        """Deploy() queues the register_custom_domain task, which registers the domain with AWS."""
        self.broker.apply(self.request, **self.kwargs)
        with patch("smarter.apps.llmclient.tasks.register_custom_domain") as register_custom_domain:
            response = self.new_broker().deploy(self.request, **self.kwargs)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        register_custom_domain.delay.assert_called_once_with(account_id=self.account.id, domain_name=DOMAIN_NAME)

    def test_deploy_not_found(self):
        with patch("smarter.apps.llmclient.tasks.register_custom_domain") as register_custom_domain:
            with self.assertRaises(SAMBrokerErrorNotFound):
                self.broker.deploy(self.request, **self.kwargs)
        register_custom_domain.delay.assert_not_called()

    def test_not_implemented(self):
        """Undeploy and prompt are not implemented."""
        for method in (self.broker.undeploy, self.broker.prompt):
            with (
                self.subTest(method=method.__name__),
                self.assertRaises((SAMBrokerErrorNotImplemented, SAMBrokerError)),
            ):
                method(self.request, **self.kwargs)
