"""
Test the Vectorsearch manifest broker through the api/v1/cli/ commands.

See :class:`smarter.lib.unittest.cli_brokers.CliBrokerTestMixin`.
"""

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.provider.models import Provider
from smarter.apps.vectorsearch.models import Vectorsearch
from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.lib.unittest.cli_brokers import CliBrokerTestMixin


class TestVectorsearchBroker(CliBrokerTestMixin, ApiV1TestBase):
    """Test the Vectorsearch broker."""

    kind = SAMKinds.VECTORSEARCH.value
    model = Vectorsearch
    name_prefix = "test_vectorsearch_broker"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # the VectorstoreMeta that the example manifest names, and its embeddings Provider.
        cls.provider = Provider.objects.create(
            name=f"test_vectorsearch_broker_provider_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            base_url="https://api.example.com/v1/",
        )
        cls.vectorstore = VectorstoreMeta.objects.create(
            name=f"test_vectorsearch_broker_store_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            embeddings_provider=cls.provider,
        )

    @classmethod
    def tearDownClass(cls):
        Vectorsearch.objects.filter(vectorstore=cls.vectorstore).delete()
        cls.vectorstore.delete()
        cls.provider.delete()
        super().tearDownClass()

    def prepare_manifest(self, manifest):
        manifest = super().prepare_manifest(manifest)
        config = manifest["spec"]["config"]
        key = "vectorstoreName" if "vectorstoreName" in config else "vectorstore_name"
        config[key] = self.vectorstore.name
        return manifest

    def test_get(self):
        super().test_get()

    def test_apply(self):
        """Test that the example manifest is applied, and applied again, which updates it."""
        self.apply()
        self.assertTrue(Vectorsearch.objects.filter(name=self.name).exists())
        self.apply()
        self.assertEqual(Vectorsearch.objects.filter(name=self.name).count(), 1)

    def test_apply_describe_delete(self):
        super().test_apply_describe_delete()
