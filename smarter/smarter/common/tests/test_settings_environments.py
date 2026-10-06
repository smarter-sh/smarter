"""
Test the Settings properties that vary by environment, and the field validators'.

error branches.
"""

import re
from unittest.mock import MagicMock, patch

from pydantic_core import ValidationError as PydanticValidationError

from smarter.common.conf import Settings, settings_defaults
from smarter.common.const import SmarterEnvironments
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib.unittest.base_classes import SmarterTestBase

CONFIG_ERRORS = (SmarterConfigurationError, PydanticValidationError)


def make_settings(**kwargs) -> Settings:
    """Return a new Settings instance with the given overrides."""
    return Settings(init_info="test_settings_environments", **kwargs)


class TestSettingsEnvironments(SmarterTestBase):
    """Test the environment-dependent domains, urls and names."""

    def test_prod_domains(self):
        """In prod, the environment domains are the root domains."""
        settings = make_settings(environment=SmarterEnvironments.PROD)
        self.assertFalse(settings.environment_is_local)
        self.assertEqual(settings.environment_platform_domain, settings.root_platform_domain)
        self.assertEqual(settings.environment_api_domain, settings.root_api_domain)
        self.assertEqual(settings.protocol, "https")
        self.assertEqual(settings.api_schema, settings_defaults.API_SCHEMA)
        self.assertEqual(settings.environment_cdn_domain, f"cdn.{settings.environment_platform_domain}")
        self.assertTrue(settings.environment_cdn_url.startswith("https://"))
        self.assertEqual(settings.root_cdn_domain, f"cdn.{settings.root_domain}")
        self.assertTrue(settings.root_cdn_url.startswith("https://"))
        self.assertTrue(settings.environment_platform_url.startswith("https://"))
        self.assertTrue(settings.environment_api_url.startswith("https://"))
        self.assertEqual(settings.aws_s3_bucket_name, settings.environment_platform_domain)
        self.assertIn(SmarterEnvironments.PROD, settings.environment_namespace)

    def test_alpha_domains(self):
        """In an AWS environment, the domains carry the environment prefix."""
        settings = make_settings(environment=SmarterEnvironments.ALPHA)
        self.assertEqual(
            settings.environment_platform_domain, f"{SmarterEnvironments.ALPHA}.{settings.root_platform_domain}"
        )
        self.assertEqual(settings.environment_api_domain, f"{SmarterEnvironments.ALPHA}.{settings.root_api_domain}")
        self.assertIn(SmarterEnvironments.ALPHA, settings.environment_namespace)

    def test_local_domains(self):
        """Locally, the domains are on localhost."""
        settings = make_settings(environment=SmarterEnvironments.LOCAL)
        self.assertTrue(settings.environment_is_local)
        self.assertEqual(settings.api_schema, "http")
        self.assertEqual(settings.protocol, "http")
        self.assertIn("localhost", settings.environment_platform_domain)
        self.assertIn("localhost", settings.environment_api_domain)
        self.assertEqual(settings.environment_cdn_domain, f"cdn.{SmarterEnvironments.LOCAL}.{settings.root_domain}")
        self.assertEqual(settings.aws_s3_bucket_name, settings.root_proxy_domain)
        self.assertTrue(settings.environment_namespace.endswith(SmarterEnvironments.LOCAL))

    def test_unknown_environment(self):
        """An environment that isn't local or AWS gets the default domain format, and no namespace."""
        settings = make_settings(environment="sandbox")
        self.assertEqual(settings.environment_platform_domain, f"sandbox.{settings.root_platform_domain}")
        self.assertEqual(settings.environment_api_domain, f"sandbox.{settings.root_api_domain}")
        with self.assertRaises(SmarterConfigurationError):
            _ = settings.environment_namespace

    def test_reactjs_app_loader_url_falls_back(self):
        """The ReactJS app loader url falls back to the default when the CDN doesn't answer."""
        settings = make_settings(environment=SmarterEnvironments.PROD)
        responses = iter([MagicMock(status_code=404), MagicMock(status_code=200)])
        with patch("smarter.common.conf.settings.requests.get", side_effect=lambda *a, **k: next(responses)):
            url = settings.smarter_reactjs_app_loader_url
        self.assertNotIn(settings.environment_cdn_domain, url)

    def test_reactjs_app_loader_url_unreachable(self):
        """When neither url answers, the intended url is returned anyway."""
        settings = make_settings(environment=SmarterEnvironments.PROD)
        with patch("smarter.common.conf.settings.requests.get", side_effect=ConnectionError("offline")):
            url = settings.smarter_reactjs_app_loader_url
        self.assertTrue(url.endswith(settings.smarter_reactjs_app_loader_path))

    def test_reactjs_app_loader_url_intended(self):
        """When the CDN answers, its url is used."""
        settings = make_settings(environment=SmarterEnvironments.PROD)
        with patch("smarter.common.conf.settings.requests.get", return_value=MagicMock(status_code=200)):
            url = settings.smarter_reactjs_app_loader_url
        self.assertTrue(url.endswith(settings.smarter_reactjs_app_loader_path))

    def test_reactjs_root_div_id_requires_the_app_loader(self):
        """The root div id can only be derived from an app-loader.js path."""
        settings = make_settings(smarter_reactjs_app_loader_path="/ui-prompt/loader.js")
        with self.assertRaises(SmarterConfigurationError):
            _ = settings.smarter_reactjs_root_div_id

    def test_versions(self):
        """The version properties report the installed versions."""
        settings = make_settings()
        for value in (
            settings.python_version,
            settings.pydantic_version,
            settings.drf_version,
            settings.django_version,
            settings.linux_distribution,
        ):
            self.assertIsInstance(value, str)
            self.assertNotIn("Unknown", value)


class TestSettingsValidators(SmarterTestBase):
    """Test the field validators' alternate inputs and error branches."""

    def test_sensitive_files_amnesty_patterns(self):
        """Patterns may be strings, compiled patterns, or a single string, but must be valid regexes."""
        compiled = re.compile(r"^/compiled/")
        settings = make_settings(sensitive_files_amnesty_patterns=[r"^/api/", compiled])
        self.assertEqual([p.pattern for p in settings.sensitive_files_amnesty_patterns], [r"^/api/", r"^/compiled/"])
        settings = make_settings(sensitive_files_amnesty_patterns=r"^/single/")
        self.assertEqual([p.pattern for p in settings.sensitive_files_amnesty_patterns], [r"^/single/"])
        settings = make_settings(sensitive_files_amnesty_patterns="")
        self.assertEqual(settings.sensitive_files_amnesty_patterns, settings_defaults.SENSITIVE_FILES_AMNESTY_PATTERNS)
        for bad in (["[unclosed"], [42], "[unclosed"):
            with self.assertRaises(CONFIG_ERRORS):
                make_settings(sensitive_files_amnesty_patterns=bad)

    def test_openai_endpoint_image_n(self):
        """The image count accepts int strings and rejects anything else."""
        self.assertEqual(make_settings(openai_endpoint_image_n="3").openai_endpoint_image_n, 3)
        for bad in ("three", 2.5):
            with self.assertRaises(CONFIG_ERRORS):
                make_settings(openai_endpoint_image_n=bad)

    def test_secret_key(self):
        """A plain string secret key is wrapped in a SecretStr."""
        settings = make_settings(secret_key="a-test-secret-key")
        self.assertEqual(settings.secret_key.get_secret_value(), "a-test-secret-key")

    def test_reactjs_app_loader_path(self):
        """The app loader path must be an absolute .js path."""
        for bad in ("ui-prompt/app-loader.js", "/ui-prompt/app-loader.css", 42):
            with self.assertRaises(CONFIG_ERRORS):
                make_settings(smarter_reactjs_app_loader_path=bad)

    def test_aws_profile_and_region_defaults(self):
        """Empty AWS profile and region fall back to the defaults."""
        settings = make_settings(aws_profile="", aws_region="")
        expected_profile = None if settings_defaults.AWS_PROFILE == "SET-ME-PLEASE" else settings_defaults.AWS_PROFILE
        self.assertIn(settings.aws_profile, (expected_profile, settings_defaults.AWS_PROFILE, None))
        self.assertIn(settings.aws_region, (settings_defaults.AWS_REGION, None))
