"""
Test the Vectorsearch /api/v1/vectorsearch/ endpoints, :mod:`smarter.apps.vectorsearch.api.v1`.

See :class:`smarter.lib.unittest.resource_api.ResourceApiTestMixin`.
"""

import unittest

from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.provider.models import Provider
from smarter.apps.vectorsearch.api.v1.urls import VectorsearchApiV1ReverseViews
from smarter.apps.vectorsearch.models import Vectorsearch
from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.lib.unittest.resource_api import ResourceApiTestMixin


class TestVectorsearchApi(ResourceApiTestMixin, ApiV1TestBase):
    """
    Test the Vectorsearch api.

    Every test that reaches a view is expected to fail, because each view is a 500:

    - ViewBase.dispatch() and ListViewBase.dispatch() assign self.user_profile after
      super().dispatch(), which has already set it, and SmarterRequestMixin.user_profile
      raises SmarterBusinessRuleViolation when it is set again.
    - VectorsearchView.dispatch() also finds the Vectorsearch only after super().dispatch()
      has called get(), patch() or delete(), which therefore never have it; patch() looks it
      up by an account field, which Vectorsearch does not have; and the urls by id are
      unreachable, because the urls by hashed id, a str, are listed first and match an id too.
    - DefaultVectorsearchApiView returns a DRF Response to a GET and an OPTIONS before DRF has
      set its renderer, which raises AssertionError.
    - test_list_with_api_key: SmarterAdminAPIView.dispatch() and SmarterAdminListAPIView.dispatch()
      check is_superuser() before DRF has authenticated the request's api key, so every request
      that is authenticated with an api key, rather than a session, is a 403.
    """

    model = Vectorsearch
    reverse_names = VectorsearchApiV1ReverseViews
    list_view = VectorsearchApiV1ReverseViews.vectorsearch_list_view
    view_by_hashed_id = VectorsearchApiV1ReverseViews.vectorsearch_view_by_hashed_id
    view_by_id = VectorsearchApiV1ReverseViews.vectorsearch_view_by_id
    default_api_by_hashed_id = VectorsearchApiV1ReverseViews.default_vectorsearch_api_view_by_hashed_id
    id_kwarg = "vectorsearch_id"
    resource_name_prefix = "test_vectorsearch_api"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.provider = Provider.objects.create(
            name=f"test_vectorsearch_api_provider_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            base_url="https://api.example.com/v1/",
        )
        cls.vectorstore = VectorstoreMeta.objects.create(
            name=f"test_vectorsearch_api_store_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            embeddings_provider=cls.provider,
        )

    @classmethod
    def tearDownClass(cls):
        Vectorsearch.objects.filter(vectorstore=cls.vectorstore).delete()
        cls.vectorstore.delete()
        cls.provider.delete()
        super().tearDownClass()

    @classmethod
    def create_resource(cls, name: str) -> Vectorsearch:
        return Vectorsearch.objects.create(name=name, user_profile=cls.user_profile, vectorstore=cls.vectorstore)

    @unittest.expectedFailure
    def test_list(self):
        super().test_list()

    @unittest.expectedFailure
    def test_list_with_api_key(self):
        super().test_list_with_api_key()

    @unittest.expectedFailure
    def test_get(self):
        super().test_get()

    @unittest.expectedFailure
    def test_get_not_found(self):
        super().test_get_not_found()

    @unittest.expectedFailure
    def test_post_invalid(self):
        super().test_post_invalid()

    @unittest.expectedFailure
    def test_patch(self):
        super().test_patch()

    @unittest.expectedFailure
    def test_delete(self):
        super().test_delete()

    @unittest.expectedFailure
    def test_default_api_get_and_options(self):
        super().test_default_api_get_and_options()
