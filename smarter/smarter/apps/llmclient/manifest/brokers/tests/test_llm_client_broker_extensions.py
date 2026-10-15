"""Test the LLMClient broker's ``spec.extensions``: linking, describing and unlinking Extensions."""

from django.test import RequestFactory

from smarter.apps.llmclient.manifest.brokers.llmclient import SAMLLMClientBroker
from smarter.apps.llmclient.models import LLMClient, LLMClientExtensions
from smarter.apps.llmtool.extension.tests.mixins import ExtensionTestMixin
from smarter.lib.manifest.broker import SAMBrokerErrorNotFound
from smarter.lib.manifest.loader import SAMLoader

NAME = "test_llmclient_broker_extensions"


def manifest(extensions: list[str]) -> str:
    """Return a minimal LLMClient manifest with the given ``spec.extensions``."""
    lines = "".join(f"    - {slug}\n" for slug in extensions)
    return (
        "apiVersion: smarter.sh/v1\nkind: LLMClient\nmetadata:\n"
        f"  name: {NAME}\n  description: x\n  version: 1.0.0\n"
        "spec:\n  config:\n    prompt:\n      provider: openai\n" + (f"  extensions:\n{lines}" if extensions else "")
    )


class TestLLMClientBrokerExtensions(ExtensionTestMixin):
    """Test applying and describing an LLMClient's extensions."""

    def tearDown(self):
        LLMClient.objects.filter(name=NAME).delete()
        super().tearDown()

    def apply(self, extensions: list[str]):
        """Apply the manifest as the test user, and return the broker and its response."""
        loader = SAMLoader(manifest=manifest(extensions))
        request = RequestFactory().post("/api/v1/cli/apply/", data=loader.manifest, content_type="application/json")
        request.user = self.admin_user
        broker = SAMLLMClientBroker(request=request, loader=loader, user_profile=self.user_profile)
        return broker, broker.apply(request=request)

    def test_apply_links_and_unlinks(self):
        """Spec.extensions links the installed extensions, and unlinks those no longer listed."""
        extension = self.install_echo()
        broker, response = self.apply(["echo"])
        self.assertEqual(response.status_code, 200, response.content[:300])
        llmclient = LLMClient.objects.get(name=NAME)
        self.assertEqual(LLMClientExtensions.extensions_for(llmclient), [extension])
        self.assertEqual(broker.extensions, ["echo"])
        self.assertEqual(broker.django_orm_to_manifest_dict()["spec"]["extensions"], ["echo"])

        _, response = self.apply([])
        self.assertEqual(response.status_code, 200, response.content[:300])
        self.assertEqual(LLMClientExtensions.extensions_for(llmclient), [])

    def test_apply_unknown_extension(self):
        """An extension that is not installed, or not available to the account, is not found."""
        with self.assertRaisesRegex(SAMBrokerErrorNotFound, "not installed, or not available"):
            self.apply(["echo"])
        extension = self.install_echo()
        extension.all_accounts = False
        extension.save()
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.apply(["echo"])
        extension.accounts.add(self.account)
        _, response = self.apply(["echo"])
        self.assertEqual(response.status_code, 200, response.content[:300])

    def test_clone_copies_extensions(self):
        """Cloning an LLMClient links the clone to the same extensions."""
        extension = self.install_echo()
        self.apply(["echo"])
        llmclient = LLMClient.objects.get(name=NAME)
        clone = llmclient.clone(new_name=f"{NAME}_clone")
        self.addCleanup(LLMClient.objects.filter(pk=clone.pk).delete)
        self.assertEqual(LLMClientExtensions.extensions_for(clone), [extension])
