"""Test SmarterAuthToken's manager, locators, tags and cached queries, which test_models.py doesn't."""

import uuid
from datetime import timedelta
from unittest.mock import patch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.drf.serializers.authtoken import (
    SmarterAuthTokenSerializer,
    SmarterCamelCaseSerializer,
)


class AuthTokenCamelCaseSerializer(SmarterCamelCaseSerializer):
    class Meta:
        model = SmarterAuthToken
        fields = ["name", "is_active", "last_used_at"]


class TestSmarterAuthTokenMore(TestAccountMixin):
    """Test SmarterAuthToken."""

    def setUp(self):
        super().setUp()
        self.token, self.key = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user_profile=self.user_profile, name="test_models_more", user=self.admin_user, description="d"
        )
        self.addCleanup(
            SmarterAuthToken.objects.filter(user_profile=self.user_profile, name__startswith="test_models_more").delete
        )

    def test_create_with_prefix_and_expiry(self):
        token, key = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user_profile=self.user_profile,
            name="test_models_more_expiry",
            user=self.admin_user,
            prefix="smr_",
            expiry=timedelta(days=1),
        )
        self.assertTrue(key.startswith("smr_"))
        self.assertIsNotNone(token.expiry)

    def test_locator(self):
        locator = self.token.record_locator
        self.assertTrue(locator.startswith("smarterauthtoken-"))
        self.assertEqual(SmarterAuthToken.get_object_by_locator(locator), self.token)
        self.assertIsNone(SmarterAuthToken.get_object_by_locator("secret-123"))
        self.assertIsNone(SmarterAuthToken.get_object_by_locator("smarterauthtoken-not-a-uuid"))
        self.assertIsNone(SmarterAuthToken.get_object_by_locator(f"smarterauthtoken-{uuid.uuid4()}"))

    def test_tags_list(self):
        self.assertEqual(self.token.tags_list, [])
        self.token.tags = ["a", 1]
        self.assertEqual(self.token.tags_list, ["a", "1"])

    def test_get_cached_objects(self):
        """Test the cached queries by user profile, by user profile and name, and by user."""
        by_profile = SmarterAuthToken.get_cached_objects(user_profile=self.user_profile, invalidate=True)
        self.assertIn(self.token, list(by_profile))
        by_name = SmarterAuthToken.get_cached_objects(
            user_profile=self.user_profile, name=self.token.name, invalidate=True
        )
        self.assertEqual(list(by_name), [self.token])
        by_user = SmarterAuthToken.get_cached_objects(user=self.admin_user, name=self.token.name, invalidate=True)
        self.assertEqual(list(by_user), [self.token])

    def test_camel_case_serializer(self):
        data = AuthTokenCamelCaseSerializer(self.token, context={"request": None}).data
        self.assertEqual(data["name"], self.token.name)
        self.assertIn("isActive", data)
        self.assertIn("lastUsedAt", data)
        self.assertIsNone(AuthTokenCamelCaseSerializer(self.token, context="not a dict").request)

    def test_identifiers(self):
        """Test that the token is identified by its key_id: it has no integer id."""
        self.assertEqual(self.token.id, str(self.token.key_id))
        self.assertEqual(self.token.hashed_id, str(self.token.key_id))
        self.assertTrue(self.token.identifier)
        self.assertNotEqual(self.token.identifier, self.token.digest)
        self.assertIn(self.token.identifier, str(self.token))

    def test_manifest_url(self):
        self.assertEqual(self.token.manifest_url, f"/authtoken/{self.token.key_id}/")

    def test_serializer_identifiers(self):
        """Test that the serializer includes the token's id and manifest url, which the web console uses."""
        data = SmarterAuthTokenSerializer(self.token, context={"request": None}).data
        self.assertEqual(data["id"], str(self.token.key_id))
        self.assertEqual(data["manifestUrl"], self.token.manifest_url)

    def test_tags_list_of_a_non_list(self):
        self.token.tags = "not a list"
        self.assertEqual(self.token.tags_list, [])

    def test_get_cached_objects_without_a_user_profile(self):
        """Without a user profile or user, the query falls back to the base class's."""
        self.assertIsNotNone(SmarterAuthToken.get_cached_objects(invalidate=True))

    def test_get_cached_objects_when_the_query_fails(self):
        """The cached queries retry without select_related() when it fails, once or twice."""
        manager = SmarterAuthToken.objects
        real = manager.select_related
        for side_effect in ([Exception("first"), real("user_profile")], Exception("always")):
            with self.subTest(side_effect=side_effect):
                with patch.object(manager, "select_related", side_effect=side_effect):
                    by_profile = SmarterAuthToken.get_cached_objects(user_profile=self.user_profile, invalidate=True)
                self.assertIn(self.token, list(by_profile))
                if isinstance(side_effect, list):
                    side_effect = [Exception("first"), real("user_profile")]
                with patch.object(manager, "select_related", side_effect=side_effect):
                    by_name = SmarterAuthToken.get_cached_objects(
                        user_profile=self.user_profile, name=self.token.name, invalidate=True
                    )
                self.assertIn(self.token, list(by_name))
