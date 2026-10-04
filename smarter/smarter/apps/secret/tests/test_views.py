"""
Test the Secret dashboard views: the React list page, its list, clone, delete and rename api,.

and the manifest detail page. See :class:`smarter.lib.unittest.resource_views.ResourceViewsTestMixin`.
"""

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.secret.caching import invalidate_all_cached_secrets_for_user_profile
from smarter.apps.secret.models import Secret
from smarter.apps.secret.urls import SecretReverseNames
from smarter.lib.unittest.resource_views import ResourceViewsTestMixin


class TestSecretViews(ResourceViewsTestMixin, TestAccountMixin):
    """Test the Secret dashboard views."""

    model = Secret
    reverse_names = SecretReverseNames
    id_kwarg = "secret_id"
    invalidate_cache = staticmethod(invalidate_all_cached_secrets_for_user_profile)
    resource_name_prefix = "test_secret_views"

    @classmethod
    def create_resource(cls, name: str) -> Secret:
        return Secret.objects.create(
            name=name, user_profile=cls.user_profile, encrypted_value=Secret.encrypt("test-secret-value")
        )

    def test_detail_hides_value(self):
        """Test that the detail page does not show the secret's value."""
        response = self.client.get(self.url("detailview", hashed_id=self.resource.hashed_id))
        self.assertNotIn(b"test-secret-value", response.content)

    def test_clone(self):
        super().test_clone()

    def test_delete(self):
        super().test_delete()

    def test_rename(self):
        super().test_rename()
