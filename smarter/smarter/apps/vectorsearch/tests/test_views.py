"""
Test the Vectorsearch dashboard views: the React list page, its list, clone, delete and rename api,.

and the manifest detail page. See :class:`smarter.lib.unittest.resource_views.ResourceViewsTestMixin`.
"""

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.provider.models import Provider
from smarter.apps.vectorsearch.caching import (
    invalidate_all_cached_vectorsearchs_for_user_profile,
)
from smarter.apps.vectorsearch.models import Vectorsearch
from smarter.apps.vectorsearch.urls import VectorsearchReverseNames
from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.lib.unittest.resource_views import ResourceViewsTestMixin


class TestVectorsearchViews(ResourceViewsTestMixin, TestAccountMixin):
    """Test the Vectorsearch dashboard views."""

    model = Vectorsearch
    reverse_names = VectorsearchReverseNames
    id_kwarg = "vectorsearch_id"
    invalidate_cache = staticmethod(invalidate_all_cached_vectorsearchs_for_user_profile)
    resource_name_prefix = "test_vectorsearch_views"

    @classmethod
    def setUpClass(cls):
        # the Vectorsearch's VectorstoreMeta, and its embeddings Provider, which
        # TestAccountMixin's account must exist for, so super().setUpClass() creates
        # them through create_resource().
        cls.provider = None
        cls.vectorstore = None
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        Vectorsearch.objects.filter(name__startswith=cls.resource_name_prefix).delete()
        if cls.vectorstore:
            cls.vectorstore.delete()
        if cls.provider:
            cls.provider.delete()
        super().tearDownClass()

    @classmethod
    def create_resource(cls, name: str) -> Vectorsearch:
        if cls.vectorstore is None:
            cls.provider = Provider.objects.create(
                name=f"test_vectorsearch_views_provider_{cls.hash_suffix}",
                user_profile=cls.user_profile,
                base_url="https://api.example.com/v1/",
            )
            cls.vectorstore = VectorstoreMeta.objects.create(
                name=f"test_vectorsearch_views_store_{cls.hash_suffix}",
                user_profile=cls.user_profile,
                embeddings_provider=cls.provider,
            )
        return Vectorsearch.objects.create(name=name, user_profile=cls.user_profile, vectorstore=cls.vectorstore)

    def test_clone(self):
        super().test_clone()

    def test_delete(self):
        super().test_delete()

    def test_rename(self):
        super().test_rename()

    def test_detail(self):
        super().test_detail()
