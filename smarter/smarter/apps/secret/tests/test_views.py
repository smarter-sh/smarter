"""
Test the Secret dashboard views: the React list page, its list, clone, delete and rename api, and the manifest detail page.

See :class:`smarter.lib.unittest.resource_views.ResourceViewsTestMixin`.
"""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import smarter_cached_objects
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


class TestSecretViewsRefusePlatformSecrets(TestAccountMixin):
    """
    Test that a user outside the platform account can't clone, or open the detail page of, a platform Secret.

    The platform account owns the provider api key Secrets. Its other resources are readable by
    every account, but a Secret holds a credential, so the clone api and the detail page must
    treat a platform Secret, and any other account's, as missing. A clone would otherwise put
    the platform's api key into the user's own account, where describe returns its value.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.platform_value = f"platform-secret-value-{cls.hash_suffix}"
        cls.platform_secret = Secret.objects.create(
            name=f"test_platform_secret_{cls.hash_suffix}",
            user_profile=smarter_cached_objects.smarter_admin_user_profile,
            encrypted_value=Secret.encrypt(cls.platform_value),
        )
        cls.account_secret = Secret.objects.create(
            name=f"test_account_secret_{cls.hash_suffix}",
            user_profile=cls.user_profile,
            encrypted_value=Secret.encrypt("account-secret-value"),
        )
        cls.staff_user, _, cls.staff_user_profile = mortal_user_factory(account=cls.account)
        cls.staff_user.is_staff = True
        cls.staff_user.save()

    @classmethod
    def tearDownClass(cls):
        Secret.objects.filter(name__startswith=f"test_platform_secret_{cls.hash_suffix}").delete()
        Secret.objects.filter(name__startswith=f"test_account_secret_{cls.hash_suffix}").delete()
        Secret.objects.filter(user_profile__account=cls.account).delete()
        # deleted directly: factory_account_teardown() would sweep every test account, also the class's own.
        cls.staff_user_profile.delete()
        cls.staff_user.delete()
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)

    def clone(self, user, secret: Secret, new_name: str):
        """POST to the clone api as ``user``, and return the response."""
        self.client.force_login(user)
        url = reverse(
            f"{SecretReverseNames.namespace}:{SecretReverseNames.listview_api_clone}",
            kwargs={"secret_id": secret.pk, "new_name": new_name},
        )
        return self.client.post(url)

    def detail(self, user, secret: Secret):
        """GET the detail page of ``secret`` as ``user``, and return the response."""
        self.client.force_login(user)
        url = reverse(
            f"{SecretReverseNames.namespace}:{SecretReverseNames.detailview}", kwargs={"hashed_id": secret.hashed_id}
        )
        return self.client.get(url)

    def test_clone_refuses_a_platform_secret(self):
        """Neither a regular user nor a staff user may clone a platform Secret into their account."""
        for user in (self.non_admin_user, self.staff_user):
            with self.subTest(user=user.username):
                new_name = f"stolen_{user.pk}_{self.hash_suffix}"
                response = self.clone(user, self.platform_secret, new_name)
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.content[:500])
                self.assertFalse(Secret.objects.filter(name=new_name).exists())
                self.assertNotIn(self.platform_value.encode(), response.content)

    def test_clone_refuses_a_colleagues_secret_for_a_regular_user(self):
        """A regular user may not clone a Secret that another user of their account owns."""
        new_name = f"colleague_copy_{self.hash_suffix}"
        response = self.clone(self.non_admin_user, self.account_secret, new_name)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.content[:500])
        self.assertFalse(Secret.objects.filter(name=new_name).exists())

    def test_clone_allows_staff_an_account_secret(self):
        """A staff user may clone a Secret that their account owns."""
        new_name = f"staff_copy_{self.hash_suffix}"
        self.addCleanup(Secret.objects.filter(name=new_name).delete)
        response = self.clone(self.staff_user, self.account_secret, new_name)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertTrue(Secret.objects.filter(name=new_name, user_profile=self.staff_user_profile).exists())

    def test_clone_allows_a_superuser_a_platform_secret(self):
        """A superuser may still clone any Secret, including a platform one."""
        new_name = f"superuser_copy_{self.hash_suffix}"
        self.addCleanup(Secret.objects.filter(name=new_name).delete)
        response = self.clone(self.admin_user, self.platform_secret, new_name)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])

    def test_detail_refuses_a_platform_secret(self):
        """Neither a regular user nor a staff user may open the detail page of a platform Secret."""
        for user in (self.non_admin_user, self.staff_user):
            with self.subTest(user=user.username):
                response = self.detail(user, self.platform_secret)
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.content[:500])
                self.assertNotIn(self.platform_value.encode(), response.content)

    def test_detail_refuses_a_colleagues_secret_for_a_regular_user(self):
        """A regular user may not open the detail page of a Secret that another user of their account owns."""
        response = self.detail(self.non_admin_user, self.account_secret)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.content[:500])
