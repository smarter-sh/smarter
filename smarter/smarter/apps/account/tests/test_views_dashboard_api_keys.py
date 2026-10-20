# pylint: disable=wrong-import-position
"""Test API Keys."""

import uuid
from http import HTTPStatus
from unittest import mock

from django.contrib.auth import authenticate
from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory

from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin

# our stuff
from smarter.apps.account.views.dashboard.api_keys import APIKeysView, APIKeyView

# python stuff
from smarter.lib import json, logging
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.typing import SmarterDictType

logger = logging.getLogger(__name__)


# pylint: disable=R0902
class TestAPIKeys(TestAccountMixin):
    """Test API Keys."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.base_url = "/account/dashboard/api-keys/"
        self.username = self.admin_user.username
        self.password = "12345"

        self.authenticated_user = authenticate(username=self.username, password=self.password)
        self.assertIsNotNone(self.authenticated_user)

        self.api_key = self.create_api_key()

        self.admin_user.set_password(self.password)
        self.admin_user.save()
        self.non_staff_authenticated_user = authenticate(username=self.non_admin_user.username, password=self.password)
        self.assertIsNotNone(self.non_staff_authenticated_user)

    def create_api_key(self):
        """Create an API Key."""
        api_key, _ = SmarterAuthToken.objects.create(
            user_profile=self.user_profile,
            name="testAPIKey",
            user=self.admin_user,
            description="Test API Key",
            is_active=True,
        )  # type: ignore
        return api_key

    def test_get_api_key(self):
        """Test that we can get an api key."""
        url = self.base_url + str(self.api_key.key_id) + "/"
        factory = RequestFactory()
        request = factory.get(url)
        request.user = self.admin_user

        response = APIKeyView.as_view()(request, key_id=self.api_key.key_id)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_get_api_key_no_permissions(self):
        """Test that we can't get an api key without permissions."""
        another_api_key, _ = SmarterAuthToken.objects.create(
            user_profile=self.user_profile,
            user=self.admin_user,
            name=self.admin_user.username,
            description="ANOTHER Test API Key",
        )  # type: ignore

        url = self.base_url + str(another_api_key.name) + "/"
        logger.debug("test_get_api_key_no_permissions() url: %s", url)
        factory = RequestFactory()
        request = factory.get(url)
        request.user = self.non_staff_authenticated_user

        response = APIKeyView.as_view()(request, key_id=self.api_key.key_id)

        # should rediredt to login page since we're not staff
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_get_api_key_not_found(self):
        """Test that we can't get an api key that doesn't exist."""
        nonexistent_api_key_id = str(uuid.uuid4())
        url = self.base_url + nonexistent_api_key_id + "/"
        factory = RequestFactory()
        request = factory.get(url)
        request.user = self.admin_user

        response = APIKeyView.as_view()(request, key_id=nonexistent_api_key_id)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @mock.patch(
        "smarter.apps.account.views.dashboard.api_keys.reverse",
        side_effect=lambda name, kwargs: f"/account/dashboard/api-keys/{kwargs['key_id']}/{kwargs['new_api_key']}/",
    )
    def test_post_api_key_not_found(self, _reverse):
        """
        Test that we can't get an api key that doesn't exist.

        The url of a new api key's page is patched: the deprecated Account UI's urls are disabled.
        """
        nonexistent_api_key_id = str(uuid.uuid4())
        url = self.base_url + nonexistent_api_key_id + "/"
        factory = RequestFactory()
        data = {}
        request = factory.post(url, data=data, content_type="application/json")
        request.user = self.admin_user

        response = APIKeyView.as_view()(request)
        self.assertIn(response.status_code, [HTTPStatus.FOUND, HTTPStatus.NOT_FOUND, HTTPStatus.BAD_REQUEST])

    def test_get_api_keys(self):
        """Test that we can get all api keys."""
        url = self.base_url
        factory = RequestFactory()
        request = factory.get(url)
        request.user = self.admin_user

        response = APIKeysView.as_view()(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_delete_nonexistent_api_key(self):
        """Test that we can't delete an api key that doesn't exist."""
        nonexistent_api_key_id = str(uuid.uuid4())
        url = self.base_url + nonexistent_api_key_id + "/"
        factory = RequestFactory()
        request = factory.delete(url)
        request.user = self.admin_user

        response = APIKeyView.as_view()(request, key_id=nonexistent_api_key_id)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


class TestAPIKeyViewRequests(TestAccountMixin):
    """
    Test the api key views' requests: create, get, update, activate, deactivate and delete.

    The deprecated Account UI's urls are disabled, so each request calls the view directly, and the
    url of a new api key's page, which the view reverses, is patched.

    A second account's admin verifies that an admin cannot see or change another account's api keys.
    The TestAccountMixin teardown deletes it.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_admin_user, cls.other_account, cls.other_user_profile = admin_user_factory()
        # admin_user_factory() users are superusers, who may see every account's api keys.
        cls.other_admin_user.is_superuser = False
        cls.other_admin_user.save()

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.user = self.admin_user
        patcher = mock.patch(
            "smarter.apps.account.views.dashboard.api_keys.reverse",
            side_effect=lambda name, kwargs: f"/account/dashboard/api-keys/{kwargs['key_id']}/{kwargs['new_api_key']}/",
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.api_key, self.token = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user_profile=self.user_profile,
            name="test_api_key_view_requests",
            user=self.admin_user,
            description="Test API Key",
            is_active=True,
        )
        self.addCleanup(SmarterAuthToken.objects.filter(pk=self.api_key.pk).delete)

    def call(self, method: str, key_id=None, new_api_key=None, data=None, content_type="application/json"):
        """Send a request to :class:`APIKeyView` as ``self.user``, with the url's ``key_id`` and ``new_api_key``."""
        request = getattr(self.factory, method)(
            "/account/dashboard/api-keys/", data=data, content_type=content_type, HTTP_HOST="testserver"
        )
        SessionMiddleware(lambda r: None).process_request(request)  # type: ignore[arg-type]
        request.user = self.user
        kwargs = {"key_id": key_id, "new_api_key": new_api_key}
        return APIKeyView.as_view()(request, **{key: value for key, value in kwargs.items() if value is not None})

    def patch_json(self, data: SmarterDictType, key_id=None):
        return self.call("patch", key_id or self.api_key.key_id, data=json.dumps(data))

    def refreshed(self) -> SmarterAuthToken:
        return SmarterAuthToken.objects.get(pk=self.api_key.pk)

    def assert_created(self, response) -> str:
        """Assert that ``response`` redirects to a new api key's page, delete the key afterwards, and return the page's url."""
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        key_id = response["Location"].rstrip("/").split("/")[-2]
        self.addCleanup(SmarterAuthToken.objects.filter(key_id=key_id).delete)
        self.assertEqual(SmarterAuthToken.objects.get(key_id=key_id).user_profile, self.user_profile)
        return response["Location"]

    def test_create_with_get(self):
        """Test that a GET of api-keys/new/ creates an api key."""
        self.assert_created(self.call("get"))

    def test_create_with_post(self):
        """Test that a POST creates an api key."""
        self.assert_created(self.call("post"))

    def test_new_api_key_page(self):
        """Test that the page that a new api key redirects to shows its token, once."""
        url = self.assert_created(self.call("post"))
        key_id, token = url.rstrip("/").split("/")[-2:]
        page = self.call("get", key_id, token)
        self.assertEqual(page.status_code, HTTPStatus.OK)
        self.assertIn(token.encode(), page.content)

    def test_get_with_wrong_token(self):
        """Test that a token that is not the api key's is a 404."""
        response = self.call("get", self.api_key.key_id, "not-the-token")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_get(self):
        """Test that the api key's page shows only the end of its token."""
        response = self.call("get", self.api_key.key_id)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotIn(self.token.encode(), response.content)

    def test_get_invalid_key_id(self):
        """Test that a key id that is not a uuid is a 404."""
        self.assertEqual(self.call("get", "not-a-uuid").status_code, HTTPStatus.NOT_FOUND)

    def test_list(self):
        request = self.factory.get("/account/dashboard/api-keys/")
        request.user = self.user
        response = APIKeysView.as_view()(request)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_patch_actions(self):
        """Test the deactivate, activate and toggle_active actions, and that an unknown action is refused."""
        self.assertEqual(self.patch_json({"action": "deactivate"}).status_code, HTTPStatus.OK)
        self.assertFalse(self.refreshed().is_active)
        self.assertEqual(self.patch_json({"action": "activate"}).status_code, HTTPStatus.OK)
        self.assertTrue(self.refreshed().is_active)
        self.assertEqual(self.patch_json({"action": "toggle_active"}).status_code, HTTPStatus.OK)
        self.assertFalse(self.refreshed().is_active)
        self.assertEqual(self.patch_json({"action": "explode"}).status_code, HTTPStatus.BAD_REQUEST)

    def test_patch_form_fields(self):
        """Test that a json PATCH without an action updates the description and is_active."""
        response = self.patch_json({"description": "updated", "is_active": False})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(self.refreshed().description, "updated")
        self.assertFalse(self.refreshed().is_active)

    def test_patch_invalid(self):
        """Test that a PATCH of an unknown api key is a 404, and of another content type is a 400."""
        self.assertEqual(self.patch_json({"action": "activate"}, key_id=uuid.uuid4()).status_code, HTTPStatus.NOT_FOUND)
        response = self.call("patch", self.api_key.key_id, data="x", content_type="text/plain")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_delete(self):
        response = self.call("delete", self.api_key.key_id)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(SmarterAuthToken.objects.filter(pk=self.api_key.pk).exists())

    def test_other_account_admin_get_and_delete(self):
        """Test that another account's admin can neither see nor delete the api key."""
        self.user = self.other_admin_user
        self.assertEqual(self.call("get", self.api_key.key_id).status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(self.call("delete", self.api_key.key_id).status_code, HTTPStatus.FORBIDDEN)
        self.assertTrue(SmarterAuthToken.objects.filter(pk=self.api_key.pk).exists())

    def test_other_account_admin_patch_json(self):
        """Test that another account's admin cannot deactivate the api key."""
        self.user = self.other_admin_user
        response = self.patch_json({"action": "deactivate"})
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertTrue(self.refreshed().is_active)
