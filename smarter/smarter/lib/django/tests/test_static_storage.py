"""Test the static files' storage on the CDN's bucket: :mod:`smarter.lib.django.static_storage`."""

from unittest.mock import patch

from cache_results import lazy_cache

from smarter.lib.django.static_storage import (
    DEFAULT_CACHE_CONTROL,
    HASHED_CACHE_CONTROL,
    UPLOADED_CACHE_KEY_PREFIX,
    SmarterStaticFilesStorage,
    cache_control,
    is_uploaded,
    mark_uploaded,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestStaticStorage(SmarterTestBase):
    """Test each static file's Cache-Control, which the storage gives its S3 object."""

    def test_a_react_build_output_is_kept_for_a_year(self):
        """A React app's built script, style or chunk has its content's hash in its name."""
        for name in (
            "react/@smarter/console/assets/index-DlE53XQD.js",
            "react/@smarter/console/assets/index-21Pn3c-f.css",
            "react/@smarter/llmclient-deployment/assets/index-DPX-GUis.css",
        ):
            with self.subTest(name=name):
                self.assertEqual(cache_control(name), HASHED_CACHE_CONTROL)

    def test_other_files_are_kept_for_an_hour(self):
        """A page, a vendored script or a theme asset keeps its name when it changes."""
        for name in (
            "react/@smarter/console/index.html",
            "react/@smarter/console/manifest.json",
            "react/@smarter/console/scalar/standalone.js",
            "assets/css/style.bundle.css",
            "react/@smarter/console/assets/logo.svg",
        ):
            with self.subTest(name=name):
                self.assertEqual(cache_control(name), DEFAULT_CACHE_CONTROL)

    def test_object_parameters(self):
        """The storage adds the file's Cache-Control to its own object parameters."""
        storage = SmarterStaticFilesStorage(
            bucket_name="platform.example.com",
            location="static",
            object_parameters={"ContentLanguage": "en"},
        )
        parameters = storage.get_object_parameters("react/@smarter/console/assets/index-DlE53XQD.js")
        self.assertEqual(parameters, {"ContentLanguage": "en", "CacheControl": HASHED_CACHE_CONTROL})
        self.assertEqual(
            storage.get_object_parameters("assets/css/style.bundle.css")["CacheControl"], DEFAULT_CACHE_CONTROL
        )
        # the storage's own parameters are not changed by a file's.
        self.assertEqual(storage.object_parameters, {"ContentLanguage": "en"})


class TestUploadedRecord(SmarterTestBase):
    """Test the record of a file's upload, which tells the console's page when to load its build from the CDN."""

    def setUp(self):
        super().setUp()
        # a name of this test's own, so that the record is never a real build's.
        self.name = f"react/@smarter/console/assets/index-{self.hash_suffix}test.js"
        self.addCleanup(lazy_cache.delete, UPLOADED_CACHE_KEY_PREFIX + self.name)

    def test_a_recorded_file_is_uploaded_without_asking_the_bucket(self):
        mark_uploaded(self.name)
        with patch("django.contrib.staticfiles.storage.staticfiles_storage.exists") as exists:
            self.assertTrue(is_uploaded(self.name))
        exists.assert_not_called()

    def test_without_a_record_the_bucket_is_asked_and_its_answer_recorded(self):
        """After the cache was cleared, a file that the bucket has is uploaded, and is recorded."""
        with patch("django.contrib.staticfiles.storage.staticfiles_storage.exists", return_value=True) as exists:
            self.assertTrue(is_uploaded(self.name))
            self.assertTrue(is_uploaded(self.name))
        exists.assert_called_once_with(self.name)

    def test_a_file_that_the_bucket_lacks_is_not_uploaded_and_not_recorded(self):
        with patch("django.contrib.staticfiles.storage.staticfiles_storage.exists", return_value=False) as exists:
            self.assertFalse(is_uploaded(self.name))
            self.assertFalse(is_uploaded(self.name))
        self.assertEqual(exists.call_count, 2)

    def test_a_bucket_that_fails_is_not_uploaded(self):
        """The page is served from the server's own /static/ rather than broken."""
        failing = patch(
            "django.contrib.staticfiles.storage.staticfiles_storage.exists", side_effect=RuntimeError("bucket")
        )
        with failing, patch("smarter.lib.django.static_storage.logger") as logger:
            self.assertFalse(is_uploaded(self.name))
        logger.warning.assert_called_once()
