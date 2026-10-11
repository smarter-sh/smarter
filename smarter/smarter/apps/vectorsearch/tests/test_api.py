"""
Test the Vectorsearch /api/v1/vectorsearch/ endpoints, :mod:`smarter.apps.vectorsearch.api.v1`.

See :class:`smarter.lib.unittest.resource_api.ResourceApiTestMixin`.
"""

from http import HTTPStatus

from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.provider.models import Provider
from smarter.apps.vectorsearch.api.v1.urls import VectorsearchApiV1ReverseViews
from smarter.apps.vectorsearch.models import Vectorsearch
from smarter.apps.vectorstore.models import VectorstoreMeta
from smarter.lib.unittest.resource_api import ResourceApiTestMixin


class TestVectorsearchApi(ResourceApiTestMixin, ApiV1TestBase):
    """Test the Vectorsearch api."""

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

    def test_list(self):
        super().test_list()

    def test_list_with_api_key(self):
        super().test_list_with_api_key()

    def test_get(self):
        super().test_get()

    def test_get_not_found(self):
        super().test_get_not_found()

    def test_post_invalid(self):
        super().test_post_invalid()

    def test_patch(self):
        super().test_patch()

    def test_delete(self):
        super().test_delete()

    def test_default_api_get_and_options(self):
        """Test that the default api refuses a GET and a POST, and says so in an OPTIONS response.

        The Vectorsearch default api is a scaffold with no POST handler yet, so its ``Allow``
        header doesn't list POST. Once it has one, call
        ``super().test_default_api_get_and_options()`` instead.
        """
        url = self.url(self.default_api_by_hashed_id, hashed_id=self.resource.hashed_id)
        self.assertEqual(self.api_client.get(url).status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(self.api_client.post(url, data={}, format="json").status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        response = self.api_client.options(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotIn("POST", response["Allow"])
