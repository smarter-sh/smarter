"""
Test the profile image: :mod:`smarter.apps.account.views.dashboard.profile_image`, UserProfile.avatar_url and get_cached_avatar_url().

Uploads are written to an in-memory storage, never to the S3 bucket that the
local containers are configured for.
"""

import io
from http import HTTPStatus

from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.files.uploadedfile import SimpleUploadedFile
from django.templatetags.static import static
from django.test import RequestFactory, override_settings
from PIL import Image

from smarter.apps.account.models import UserProfile
from smarter.apps.account.models.user_profile import (
    DEFAULT_PROFILE_IMAGE,
    profile_image_upload_to,
)
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.utils import get_cached_avatar_url
from smarter.apps.account.views.dashboard import profile_image
from smarter.apps.account.views.dashboard.profile_image import ProfileImageView
from smarter.lib import json

OAUTH_IMAGE = "https://example.com/oauth-picture.png"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage", "OPTIONS": {"base_url": "/media/"}},
    "staticfiles": settings.STORAGES["staticfiles"],
}


def image_file(name: str = "me.png", image_format: str = "PNG", content_type: str = "image/png") -> SimpleUploadedFile:
    """Return a small, valid image file to upload."""
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color=(255, 0, 0)).save(buffer, format=image_format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=content_type)


class TestProfileImage(TestAccountMixin):
    """Upload, replace and remove a profile image, and resolve the image that the console shows."""

    def setUp(self):
        super().setUp()
        # SmarterTestBase is a unittest.TestCase, which override_settings can't decorate.
        storages = override_settings(STORAGES=STORAGES)
        storages.enable()
        self.addCleanup(storages.disable)
        self.factory = RequestFactory()
        self.addCleanup(self.reset_profile)

    def reset_profile(self):
        UserProfile.objects.filter(pk=self.non_admin_user_profile.pk).update(profile_image=None, profile_image_url=None)
        get_cached_avatar_url(user_id=self.non_admin_user.id, invalidate=True)

    def profile(self) -> UserProfile:
        return UserProfile.objects.get(pk=self.non_admin_user_profile.pk)

    def call(self, method: str, data=None):
        request = getattr(self.factory, method)("/account/dashboard/profile-image/", data=data or {})
        SessionMiddleware(lambda r: None).process_request(request)  # type: ignore[arg-type]
        request.user = self.non_admin_user
        return ProfileImageView.as_view()(request)

    def test_default_profile_image(self):
        """Test that a user with neither an upload nor an oauth image gets the default image."""
        self.assertEqual(self.profile().avatar_url, static(DEFAULT_PROFILE_IMAGE))
        self.assertEqual(get_cached_avatar_url(user_id=self.non_admin_user.id), static(DEFAULT_PROFILE_IMAGE))
        self.assertTrue(static(DEFAULT_PROFILE_IMAGE).endswith(".svg"))

    def test_oauth_profile_image(self):
        UserProfile.objects.filter(pk=self.non_admin_user_profile.pk).update(profile_image_url=OAUTH_IMAGE)
        self.assertEqual(get_cached_avatar_url(user_id=self.non_admin_user.id, invalidate=True), OAUTH_IMAGE)

    def test_upload_takes_precedence_over_oauth(self):
        """Test that an upload replaces the image shown, that its replacement deletes it, and removing it restores the oauth image."""
        UserProfile.objects.filter(pk=self.non_admin_user_profile.pk).update(profile_image_url=OAUTH_IMAGE)
        response = self.call("post", {"profile_image": image_file()})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        first = self.profile().profile_image
        self.assertTrue(first.name.startswith("account/profile_images/"))
        self.assertTrue(first.name.endswith(".png"))
        self.assertNotIn("me", first.name)
        url = json.loads(response.content)["profile_image_url"]
        self.assertTrue(url.startswith("http"), url)
        self.assertTrue(url.endswith(first.name), url)
        self.assertEqual(get_cached_avatar_url(user_id=self.non_admin_user.id), url)

        self.assertEqual(self.call("post", {"profile_image": image_file("me.jpg", "JPEG")}).status_code, HTTPStatus.OK)
        second = self.profile().profile_image
        self.assertNotEqual(second.name, first.name)
        self.assertFalse(second.storage.exists(first.name))

        response = self.call("delete")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(json.loads(response.content)["profile_image_url"], OAUTH_IMAGE)
        self.assertFalse(self.profile().profile_image)
        self.assertFalse(second.storage.exists(second.name))
        self.assertEqual(self.call("delete").status_code, HTTPStatus.OK)

    def test_upload_for_unnamed_profile(self):
        """Test an upload for a profile with a blank name, as the oauth pipeline and older installs create them."""
        name = self.non_admin_user_profile.name
        UserProfile.objects.filter(pk=self.non_admin_user_profile.pk).update(name="")
        self.addCleanup(UserProfile.objects.filter(pk=self.non_admin_user_profile.pk).update, name=name)
        self.assertEqual(self.call("post", {"profile_image": image_file()}).status_code, HTTPStatus.OK)
        self.assertTrue(self.profile().profile_image)

    def test_invalid_uploads(self):
        """Test that a missing file, a file that isn't an image, an svg and a large image are refused."""
        svg = SimpleUploadedFile("me.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>", content_type="image/svg+xml")
        for data in (
            {},
            {"profile_image": SimpleUploadedFile("me.png", b"not an image", content_type="image/png")},
            {"profile_image": svg},
            {"profile_image": image_file("me.bmp", "BMP", "image/bmp")},
        ):
            with self.subTest(data=data):
                response = self.call("post", data)
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
                self.assertIn("profile_image", json.loads(response.content))
        original = profile_image.PROFILE_IMAGE_MAX_BYTES
        profile_image.PROFILE_IMAGE_MAX_BYTES = 10
        self.addCleanup(setattr, profile_image, "PROFILE_IMAGE_MAX_BYTES", original)
        self.assertEqual(self.call("post", {"profile_image": image_file()}).status_code, HTTPStatus.BAD_REQUEST)
        self.assertFalse(self.profile().profile_image)

    def test_user_without_profile(self):
        """Test that a user with no UserProfile gets the default image."""
        user = type(self.non_admin_user).objects.create(username=f"test_profile_image_{self.hash_suffix}")
        self.addCleanup(user.delete)
        self.assertEqual(get_cached_avatar_url(user_id=user.id), static(DEFAULT_PROFILE_IMAGE))

    def test_upload_to(self):
        self.assertRegex(profile_image_upload_to(None, "Photo.JPG"), r"^account/profile_images/[0-9a-f]{32}\.jpg$")  # type: ignore[arg-type]
