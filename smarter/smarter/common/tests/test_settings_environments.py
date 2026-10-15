"""
Test the Settings properties that vary by environment, and the field validators'.

error branches.
"""

import re
from unittest.mock import patch

from pydantic_core import ValidationError as PydanticValidationError

from smarter.common.conf import Settings, settings_defaults
from smarter.common.conf.settings import validate_throttle_rate
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

    def test_secret_key_is_set(self):
        """A configured key is set; a placeholder, or the key generated by settings_defaults, is not."""
        self.assertTrue(make_settings(secret_key="a-configured-secret-key").secret_key_is_set)
        self.assertFalse(make_settings(secret_key="SET-ME-IN-helm/charts/smarter/values.yaml").secret_key_is_set)
        generated = settings_defaults.SECRET_KEY.get_secret_value()
        with patch.object(settings_defaults, "SECRET_KEY_IS_GENERATED", True):
            self.assertFalse(make_settings(secret_key=generated).secret_key_is_set)
            self.assertTrue(make_settings(secret_key="a-configured-secret-key").secret_key_is_set)
        with patch.object(settings_defaults, "SECRET_KEY_IS_GENERATED", False):
            self.assertTrue(make_settings(secret_key=generated).secret_key_is_set)

    def test_require_secret_key(self):
        """Outside of the local environment, a missing secret key is fatal; locally, it is a warning."""
        placeholder = "SET-ME-IN-helm/charts/smarter/values.yaml"
        for environment in SmarterEnvironments.aws_environments:
            with self.assertRaises(SmarterConfigurationError):
                make_settings(environment=environment, secret_key=placeholder).require_secret_key()
            make_settings(environment=environment, secret_key="a-configured-secret-key").require_secret_key()
        with self.assertLogs("smarter.common.conf.settings", level="WARNING"):
            make_settings(environment=SmarterEnvironments.LOCAL, secret_key=placeholder).require_secret_key()

    def test_throttle_rates(self):
        """Throttle rates accept DRF rates and the disabled values, and reject anything else."""
        settings = make_settings(throttle_rate_anon=" 10/Second ", throttle_rate_user="none")
        self.assertEqual(settings.throttle_rate_anon, "10/second")
        self.assertIsNone(settings.throttle_rate_user)
        settings = make_settings(throttle_rate_anon="", throttle_rate_user=None)
        self.assertEqual(settings.throttle_rate_anon, settings_defaults.THROTTLE_RATE_ANON)
        self.assertEqual(settings.throttle_rate_user, settings_defaults.THROTTLE_RATE_USER)
        for disabled in ("off", "Disabled", "NONE"):
            self.assertIsNone(validate_throttle_rate("throttle_rate_anon", disabled, "1/day"))
        for bad in ("lots", "10", "10/fortnight", "/minute", 10):
            with self.assertRaises(CONFIG_ERRORS):
                make_settings(throttle_rate_anon=bad)

    def test_aws_profile_and_region_defaults(self):
        """Empty AWS profile and region fall back to the defaults."""
        settings = make_settings(aws_profile="", aws_region="")
        expected_profile = None if settings_defaults.AWS_PROFILE == "SET-ME-PLEASE" else settings_defaults.AWS_PROFILE
        self.assertIn(settings.aws_profile, (expected_profile, settings_defaults.AWS_PROFILE, None))
        self.assertIn(settings.aws_region, (settings_defaults.AWS_REGION, None))
