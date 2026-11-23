"""Test the LLMClient broker's ``spec.vectorsearches``: linking, describing, cloning and unlinking Vectorsearches."""

from django.test import RequestFactory

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.llmclient.contract.models import LLMClientApiLLMClient
from smarter.apps.llmclient.manifest.brokers.llmclient import SAMLLMClientBroker
from smarter.apps.llmclient.models import LLMClient, LLMClientVectorsearches
from smarter.apps.llmclient.models.utils import get_cached_llmclient_tool_counts
from smarter.apps.llmclient.serializers import LLMClientSerializer
from smarter.apps.vectorsearch.manifest.brokers.vectorsearch import (
    SAMVectorsearchBroker,
)
from smarter.apps.vectorsearch.models import Vectorsearch
from smarter.apps.vectorstore.tests.base_classes import VectorstoreTestBase
from smarter.lib.manifest.broker import SAMBrokerErrorNotFound
from smarter.lib.manifest.parsing import parse_manifest

NAME = "test_llmclient_broker_vectorsearches"


def manifest(vectorsearches: list[str]) -> str:
    """Return a minimal LLMClient manifest with the given ``spec.vectorsearches``."""
    lines = "".join(f"    - {name}\n" for name in vectorsearches)
    return (
        "apiVersion: smarter.sh/v1\nkind: LLMClient\nmetadata:\n"
        f"  name: {NAME}\n  description: x\n  version: 1.0.0\n"
        "spec:\n  config:\n    prompt:\n      provider: openai\n"
        + (f"  vectorsearches:\n{lines}" if vectorsearches else "")
    )


class TestLLMClientBrokerVectorsearches(VectorstoreTestBase):
    """Test applying, describing and cloning an LLMClient's Vectorsearches."""

    vectorsearch: Vectorsearch

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        vectorstore = cls.new_vectorstore_for_class()
        cls.vectorsearch = Vectorsearch.objects.create(
            name=f"handbook_{cls.hash_suffix}",
            description="Searches the handbook.",
            user_profile=cls.user_profile,
            vectorstore=vectorstore,
        )

    @classmethod
    def new_vectorstore_for_class(cls):
        """A Vectorstore for the whole class; never deployed, since nothing here searches it."""
        # pylint: disable=import-outside-toplevel
        from smarter.apps.vectorstore.models import VectorstoreMeta

        return VectorstoreMeta.objects.create(
            name=f"handbook_store_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            spec={},
            backend="qdrant",
            hosting="self_hosted",
            dimension=32,
            metric="cosine",
            embeddings_provider=cls.provider,
            embeddings_model="test-embedding",
        )

    @classmethod
    def tearDownClass(cls):
        LLMClient.objects.filter(name__startswith=NAME).delete()
        cls.vectorsearch.delete()
        super().tearDownClass()

    def tearDown(self):
        LLMClient.objects.filter(name__startswith=NAME).delete()
        super().tearDown()

    def apply(self, vectorsearches: list[str]):
        """Apply the manifest as the test user, and return the broker and its response."""
        manifest_data = parse_manifest(manifest(vectorsearches))
        request = RequestFactory().post("/api/v1/cli/apply/", data=manifest_data, content_type="application/json")
        request.user = self.admin_user
        broker = SAMLLMClientBroker(request=request, manifest=manifest_data, user_profile=self.user_profile)
        return broker, broker.apply(request=request)

    def test_apply_links_and_unlinks(self):
        """Spec.vectorsearches links the Vectorsearches, describe lists them, and an apply without them unlinks them."""
        broker, response = self.apply([self.vectorsearch.name])
        self.assertEqual(response.status_code, 200, response.content[:300])
        llmclient = LLMClient.objects.get(name=NAME)
        self.assertEqual(LLMClientVectorsearches.vectorsearches_for(llmclient), [self.vectorsearch])
        described = broker.django_orm_to_manifest_dict()
        assert described is not None
        self.assertEqual(described["spec"]["vectorsearches"], [self.vectorsearch.name])

        before_detach = LLMClient.objects.get(pk=llmclient.pk).updated_at
        broker, response = self.apply([])
        self.assertEqual(response.status_code, 200, response.content[:300])
        self.assertEqual(LLMClientVectorsearches.vectorsearches_for(llmclient), [])
        described = broker.django_orm_to_manifest_dict()
        assert described is not None
        self.assertIsNone(described["spec"]["vectorsearches"])
        # what the llmclient uses changed, so its cached answers must not be used: see touch_when_relations_changed().
        self.assertGreater(LLMClient.objects.get(pk=llmclient.pk).updated_at, before_detach)

    def test_apply_unknown_vectorsearch(self):
        """A Vectorsearch that doesn't exist, or isn't shared with the user, is not found."""
        with self.assertRaisesRegex(SAMBrokerErrorNotFound, "not found, or not shared"):
            self.apply(["no_such_vectorsearch"])

    def test_a_disabled_vectorsearch_is_linked_but_not_offered(self):
        """A disabled Vectorsearch stays linked, but vectorsearches_for() leaves it out, so the LLM isn't offered it."""
        self.apply([self.vectorsearch.name])
        llmclient = LLMClient.objects.get(name=NAME)
        Vectorsearch.objects.filter(pk=self.vectorsearch.pk).update(is_enabled=False)
        self.addCleanup(Vectorsearch.objects.filter(pk=self.vectorsearch.pk).update, is_enabled=True)
        self.assertTrue(LLMClientVectorsearches.objects.filter(llmclient=llmclient).exists())
        self.assertEqual(LLMClientVectorsearches.vectorsearches_for(llmclient), [])

    def test_the_vectorsearch_knows_its_llmclients(self):
        """The Vectorsearch broker's dependents are the LLMClients that use it, so it can't be deleted under them."""
        self.apply([self.vectorsearch.name])
        llmclient = LLMClient.objects.get(name=NAME)
        dependents = SAMVectorsearchBroker.dependents(self.vectorsearch)
        self.assertEqual(dependents[0][0], SAMKinds.LLM_CLIENT.value)
        self.assertEqual(list(dependents[0][1]), [llmclient])
        references = dict(SAMLLMClientBroker.references(llmclient))  # type: ignore[arg-type]
        self.assertEqual(list(references[SAMKinds.VECTORSEARCH.value]), [self.vectorsearch])

    def test_clone_copies_vectorsearches(self):
        """Cloning an LLMClient links the clone to the same Vectorsearches."""
        self.apply([self.vectorsearch.name])
        llmclient = LLMClient.objects.get(name=NAME)
        clone = llmclient.clone(new_name=f"{NAME}_clone")
        self.assertEqual(LLMClientVectorsearches.vectorsearches_for(clone), [self.vectorsearch])

    def test_a_vectorsearch_is_one_of_the_llmclients_tools(self):
        """The tool counts, the serializer and the api contract all count a Vectorsearch as a tool."""
        self.apply([self.vectorsearch.name])
        llmclient = LLMClient.objects.get(name=NAME)
        counts = get_cached_llmclient_tool_counts(llmclient.pk)
        self.assertEqual(counts.vectorsearches, 1)
        self.assertEqual(counts.total, 1)

        data = LLMClientSerializer(llmclient).data
        self.assertEqual([row["name"] for row in data["vectorsearches"]], [self.vectorsearch.name])
        self.assertIn(
            {"id": data["vectorsearches"][0]["id"], "name": self.vectorsearch.name, "kind": "Vectorsearch"},
            data["tools"],
        )

        contract = LLMClientApiLLMClient.from_model(llmclient, self.admin_user)
        self.assertEqual([ref.name for ref in contract.vectorsearches], [self.vectorsearch.name])
        self.assertIn("Vectorsearch", [tool.kind for tool in contract.tools])
