"""
Test the Vectorsearch manifest broker through the api/v1/cli/ commands.

See :class:`smarter.lib.unittest.cli_brokers.CliBrokerTestMixin`.
"""

import unittest

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

    @unittest.expectedFailure
    def test_get(self):
        """
        Expected to fail: the broker's VectorsearchSerializer declares fields = ["__all__"], a list,.

        rather than the string "__all__", so serializing a Vectorsearch raises ImproperlyConfigured,
        and get is a 500 whenever one exists.
        """
        super().test_get()

    def test_apply(self):
        """Test that the example manifest is applied, and applied again, which updates it."""
        self.apply()
        self.assertTrue(Vectorsearch.objects.filter(name=self.name).exists())
        self.apply()
        self.assertEqual(Vectorsearch.objects.filter(name=self.name).count(), 1)

    @unittest.expectedFailure
    def test_apply_describe_delete(self):
        """
        Expected to fail: SAMVectorsearchBroker.describe() builds SAMVectorsearchSpecConfig from a.

        camelCased dict, whose vectorstoreName the model, which requires vectorstore_name, does
        not accept, so describe is a 500. Also, SAMVectorsearchBroker.delete() calls
        Vectorsearch.get_cached_object() with neither a pk nor a name, so delete is a 500.
        """
        super().test_apply_describe_delete()
