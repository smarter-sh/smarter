"""
Test the Settings properties that vary by environment, and the field validators'.

error branches.
"""

import os
import warnings
from unittest.mock import patch

from pydantic import SecretStr
from pydantic_core import ValidationError as PydanticValidationError

from smarter.common.conf import Settings
from smarter.common.conf.settings import security
from smarter.common.conf.util import validate_throttle_rate
from smarter.common.const import SmarterEnvironments, SmarterKubernetesPodKinds
from smarter.common.exceptions import SmarterConfigurationError, SmarterValueError
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.environment import as_restricted_worker

CONFIG_ERRORS = (SmarterConfigurationError, PydanticValidationError)


def make_settings(**kwargs) -> Settings:
    """Return a new Settings instance with the given overrides."""
    return Settings(**kwargs)


class TestSettingsEnvironments(SmarterTestBase):
    """Test the environment-dependent domains, urls and names."""

    def test_prod_domains(self):
        """In prod, the environment domains are the root domains."""
        settings = make_settings(environment=SmarterEnvironments.PROD)
        self.assertFalse(settings.environment_is_local)
        self.assertEqual(settings.environment_platform_domain, settings.root_platform_domain)
        self.assertEqual(settings.environment_api_domain, settings.root_api_domain)
        self.assertEqual(settings.environment_api_dns_domain, settings.environment_api_domain)
        self.assertEqual(settings.protocol, "https")
        self.assertIn(settings.api_schema, ("http", "https"))
        self.assertEqual(settings.environment_cdn_domain, f"cdn.{settings.environment_platform_domain}")
        self.assertTrue(settings.environment_cdn_url.startswith("https://"))
        self.assertEqual(settings.root_cdn_domain, f"cdn.{settings.platform_root_domain}")
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
        self.assertEqual(settings.environment_api_dns_domain, settings.environment_api_domain)
        self.assertIn(SmarterEnvironments.ALPHA, settings.environment_namespace)

    def test_local_domains(self):
        """Locally, the domains are on localhost."""
        settings = make_settings(environment=SmarterEnvironments.LOCAL)
        self.assertTrue(settings.environment_is_local)
        self.assertEqual(settings.api_schema, "http")
        self.assertEqual(settings.protocol, "http")
        self.assertIn("localhost", settings.environment_platform_domain)
        self.assertIn("localhost", settings.environment_api_domain)
        # DNS can't serve localhost: LLMClients' records, and their ClusterIssuer, use the proxy domain,
        # api.local.<root domain>, which smarter-infrastructure's local environment creates.
        self.assertEqual(
            settings.environment_api_dns_domain, f"api.{SmarterEnvironments.LOCAL}.{settings.platform_root_domain}"
        )
        self.assertEqual(settings.environment_api_dns_domain, settings.proxy_api_domain)
        self.assertEqual(
            settings.environment_cdn_domain, f"cdn.{SmarterEnvironments.LOCAL}.{settings.platform_root_domain}"
        )
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

    def test_secret_key(self):
        """A plain string secret key is wrapped in a SecretStr."""
        settings = make_settings(django_secret_key="a-test-secret-key")
        assert settings.django_secret_key is not None
        self.assertEqual(settings.django_secret_key.get_secret_value(), "a-test-secret-key")

    def test_secret_key_is_set(self):
        """A configured key is set; a placeholder, or the key that the process generated, is not."""
        self.assertTrue(make_settings(django_secret_key="a-configured-secret-key").django_secret_key_is_set)
        self.assertFalse(
            make_settings(django_secret_key="SET-ME-IN-helm/charts/smarter/values.yaml").django_secret_key_is_set
        )
        with patch.object(security, "_generated_django_secret_key", None):
            with self.assertWarns(UserWarning):
                generated = security.generated_django_secret_key()
            self.assertIs(security.generated_django_secret_key(), generated)
            self.assertFalse(make_settings(django_secret_key=generated).django_secret_key_is_set)
            self.assertTrue(make_settings(django_secret_key="a-configured-secret-key").django_secret_key_is_set)
        with patch.object(security, "_generated_django_secret_key", None):
            self.assertTrue(make_settings(django_secret_key=generated.get_secret_value()).django_secret_key_is_set)

    def test_generated_fernet_encryption_key(self):
        """Without a configured key, the process generates one, once, with a warning."""
        with patch.object(security, "_generated_fernet_encryption_key", None):
            with self.assertWarns(UserWarning):
                generated = security.generated_fernet_encryption_key()
            self.assertIs(security.generated_fernet_encryption_key(), generated)
            self.assertEqual(len(generated.get_secret_value()), 44)

    def test_the_tool_worker_generates_its_keys_quietly(self):
        """The tool worker is never given the keys (ADR-038), so it generates both without a warning."""
        with (
            patch.dict(os.environ, {security.DATABASE_UNAVAILABLE_VARIABLE: "true"}),
            patch.object(security, "_generated_django_secret_key", None),
            patch.object(security, "_generated_fernet_encryption_key", None),
            warnings.catch_warnings(record=True) as caught,
        ):
            warnings.simplefilter("always")
            secret_key = security.generated_django_secret_key()
            fernet_key = security.generated_fernet_encryption_key()
        self.assertTrue(secret_key.get_secret_value())
        self.assertEqual(len(fernet_key.get_secret_value()), 44)
        self.assertEqual(caught, [])

    def test_is_tool_worker(self):
        """The tool worker is recognized by SMARTER_DATABASE_UNAVAILABLE, which the Helm chart sets for it only."""
        with patch.dict(os.environ, {security.DATABASE_UNAVAILABLE_VARIABLE: "true"}):
            self.assertTrue(security.is_tool_worker())
        with patch.dict(os.environ, {security.DATABASE_UNAVAILABLE_VARIABLE: "false"}):
            self.assertFalse(security.is_tool_worker())

    def test_require_secret_key(self):
        """Outside of the local environment, a missing secret key is fatal; locally, it is a warning."""
        placeholder = "SET-ME-IN-helm/charts/smarter/values.yaml"
        for environment in SmarterEnvironments.aws_environments:
            with self.assertRaises(SmarterConfigurationError):
                make_settings(environment=environment, django_secret_key=placeholder).require_django_secret_key()
            make_settings(
                environment=environment, django_secret_key="a-configured-secret-key"
            ).require_django_secret_key()
            # the tool worker, which has no database, is never given the key.
            with as_restricted_worker():
                make_settings(
                    environment=environment, django_secret_key=placeholder, database_unavailable=True
                ).require_django_secret_key()
        with self.assertLogs("smarter.common.conf.settings", level="WARNING"):
            make_settings(
                environment=SmarterEnvironments.LOCAL, django_secret_key=placeholder
            ).require_django_secret_key()

    def test_require_redis_password(self):
        """Outside of the local environment, a missing Redis password is fatal; locally, it is docker-compose's."""
        placeholder = "SET-ME-IN-helm/charts/smarter/values.yaml"
        for environment in SmarterEnvironments.aws_environments:
            settings = make_settings(environment=environment, subsystem_redis_password=placeholder)
            self.assertIsNone(settings.subsystem_redis_password)
            with self.assertRaises(SmarterConfigurationError):
                settings.require_redis_password()
            settings = make_settings(environment=environment, subsystem_redis_password="GeneratedRedisPassword1")
            password = settings.require_redis_password()
            self.assertEqual(password.get_secret_value(), "GeneratedRedisPassword1")
            # the tool worker needs it too: it takes its tasks from the broker.
            with as_restricted_worker():
                settings = make_settings(
                    environment=environment, subsystem_redis_password="", database_unavailable=True
                )
            with self.assertRaises(SmarterConfigurationError):
                settings.require_redis_password()
        settings = make_settings(environment=SmarterEnvironments.LOCAL, subsystem_redis_password="")
        self.assertEqual(settings.require_redis_password().get_secret_value(), "smarter")

    def test_redis_username(self):
        """Empty or a placeholder is Redis's default user; a username is trimmed."""
        self.assertIsNone(make_settings(subsystem_redis_username="").subsystem_redis_username)
        placeholder = "SET-ME-IN-helm/charts/smarter/values.yaml"
        self.assertIsNone(make_settings(subsystem_redis_username=placeholder).subsystem_redis_username)
        self.assertEqual(make_settings(subsystem_redis_username=" tools ").subsystem_redis_username, "tools")

    def test_tool_worker_queue(self):
        """A worker without a database is the tool worker, unless its queue is the Extensions queue (issue #1077)."""
        with as_restricted_worker():
            tool_worker = make_settings(database_unavailable=True, app_tools_worker_queue="")
            extension_worker = make_settings(
                database_unavailable=True, app_tools_worker_queue=" extensions_celery_task_queue "
            )
        settings = tool_worker
        self.assertEqual(settings.tool_worker_queue, "tools_celery_task_queue")
        self.assertFalse(settings.is_extension_worker)
        settings = extension_worker
        self.assertEqual(settings.tool_worker_queue, "extensions_celery_task_queue")
        self.assertTrue(settings.is_extension_worker)
        # a process with a database is no worker of either kind, whatever the setting says.
        settings = make_settings(database_unavailable=False, app_tools_worker_queue="extensions_celery_task_queue")
        self.assertFalse(settings.is_extension_worker)
        self.assertEqual(make_settings().app_extensions_tasks_celery_task_queue, "extensions_celery_task_queue")

    def test_redis_password_is_masked(self):
        """The Redis password is a SecretStr, so a dump of the settings never shows it."""
        settings = make_settings(subsystem_redis_password="GeneratedRedisPassword1")
        self.assertIsInstance(settings.subsystem_redis_password, SecretStr)
        self.assertNotIn("GeneratedRedisPassword1", repr(settings))
        self.assertNotIn("GeneratedRedisPassword1", str(settings.model_dump()))

    def test_throttle_rates(self):
        """Throttle rates accept DRF rates and the disabled values, and reject anything else."""
        settings = make_settings(app_api_throttle_rate_anon=" 10/Second ", app_api_throttle_rate_user="none")
        self.assertEqual(settings.app_api_throttle_rate_anon, "10/second")
        self.assertIsNone(settings.app_api_throttle_rate_user)
        settings = make_settings(app_api_throttle_rate_anon="", app_api_throttle_rate_user=None)
        self.assertEqual(settings.app_api_throttle_rate_anon, "120/minute")
        self.assertEqual(settings.app_api_throttle_rate_user, "600/minute")
        for disabled in ("off", "Disabled", "NONE"):
            self.assertIsNone(validate_throttle_rate("throttle_rate_anon", disabled, "1/day"))
        for bad in ("lots", "10", "10/fortnight", "/minute", 10):
            with self.assertRaises(CONFIG_ERRORS):
                make_settings(app_api_throttle_rate_anon=bad)

    def test_quoted_environment_variables(self):
        """A quoted value, as make exports .env's lines, is read without its quotes, a secret too."""
        quoted = {
            "SMARTER_PLATFORM_BRANDING_CONTACT_URL": '"https://example.com/contact/"',
            "DJANGO_SECRET_KEY": "'a-quoted-secret-key'",
        }
        with patch.dict(os.environ, quoted):
            settings = make_settings()
        self.assertEqual(str(settings.platform_branding_contact_url), "https://example.com/contact/")
        assert settings.django_secret_key is not None
        self.assertEqual(settings.django_secret_key.get_secret_value(), "a-quoted-secret-key")

    def test_aws_profile_and_region_defaults(self):
        """Empty AWS profile and region fall back to their defaults, None."""
        settings = make_settings(aws_profile="", aws_region="")
        self.assertIsNone(settings.aws_profile)
        self.assertIsNone(settings.aws_region)


class TestDerivedDefaults(SmarterTestBase):
    """The defaults that depend on another field are derived from it, unless they are set."""

    def test_from_the_root_domain(self):
        """Without SMTP_SENDER, which the test stacks' .env sets, the sender is derived."""
        with patch.dict(os.environ, {"SUBSYSTEM_SMTP_SENDER": "", "SMARTER_SUBSYSTEM_SMTP_SENDER": ""}):
            os.environ.pop("SUBSYSTEM_SMTP_SENDER")
            os.environ.pop("SMARTER_SUBSYSTEM_SMTP_SENDER")
            settings = make_settings(platform_root_domain="smarter.sh")
        self.assertEqual(settings.subsystem_smtp_sender, "admin@smarter.sh")
        self.assertEqual(str(settings.platform_branding_marketing_site_url), "https://smarter.sh/")

    def test_from_the_cdn(self):
        settings = make_settings(platform_branding_cdn_url="https://cdn.smarter.sh")
        self.assertEqual(str(settings.platform_branding_logo), "https://cdn.smarter.sh/images/logo/smarter-crop.png")

    def test_set_values_win(self):
        settings = make_settings(
            platform_root_domain="smarter.sh",
            subsystem_smtp_sender="sender@example.com",
            platform_branding_marketing_site_url="https://www.example.com",
            platform_branding_logo="https://cdn.example.com/logo.png",
        )
        self.assertEqual(settings.subsystem_smtp_sender, "sender@example.com")
        self.assertEqual(str(settings.platform_branding_marketing_site_url), "https://www.example.com/")
        self.assertEqual(str(settings.platform_branding_logo), "https://cdn.example.com/logo.png")

    def test_local_database_password(self):
        """Locally, the database password is docker-compose.yml's; elsewhere there is none."""
        local = make_settings(environment=SmarterEnvironments.LOCAL, subsystem_sql_password="")
        assert local.subsystem_sql_password is not None
        self.assertEqual(local.subsystem_sql_password.get_secret_value(), "smarter")
        prod = make_settings(environment=SmarterEnvironments.PROD, subsystem_sql_password="")
        self.assertIsNone(prod.subsystem_sql_password)

    def test_log_level(self):
        """A level's name or its number; derived from debug_mode unless it is set."""
        self.assertEqual(make_settings(log_level="warning").log_level, 30)
        self.assertEqual(make_settings(log_level="40").log_level, 40)
        for bad in ("LOUD", True, 1.5):
            with self.assertRaises(CONFIG_ERRORS):
                make_settings(log_level=bad)

    def test_log_level_from_debug_mode(self):
        """Without SMARTER_LOG_LEVEL, which the test stacks' .env sets, the level follows debug_mode."""
        with patch.dict(os.environ, {"SMARTER_LOG_LEVEL": ""}):
            os.environ.pop("SMARTER_LOG_LEVEL")
            self._assert_log_level_from_debug_mode()

    def _assert_log_level_from_debug_mode(self):
        self.assertEqual(make_settings(debug_mode=True).log_level, 10)
        self.assertEqual(make_settings(debug_mode=False).log_level, 20)
        self.assertEqual(make_settings(debug_mode="true").log_level, 10)
        self.assertEqual(make_settings(debug_mode=True, log_level=30).log_level, 30)

    def test_field_defaults(self):
        """The settings dump lists each field's declared default, without making a factory's."""
        defaults = make_settings().field_defaults()
        self.assertEqual(defaults["platform_root_domain"], "example.com")
        self.assertEqual(defaults["django_secret_key"], "<generated_django_secret_key()>")


class TestDomainsAndSchema(SmarterTestBase):
    """Allowed_hosts is complete, with the platform's domains; api_schema is http locally."""

    def test_allowed_hosts_include_the_platforms_domains(self):
        settings = make_settings(environment=SmarterEnvironments.PROD, allowed_hosts=["extra.example.com:8000"])
        self.assertIn("extra.example.com:8000", settings.allowed_hosts)
        self.assertIn("extra.example.com", settings.allowed_hosts)
        self.assertIn(settings.environment_platform_domain, settings.allowed_hosts)
        self.assertIn(f".{settings.environment_api_domain}", settings.allowed_hosts)
        with self.assertRaises((*CONFIG_ERRORS, SmarterValueError)):
            make_settings(allowed_hosts=["not a host!"])

    def test_api_schema(self):
        self.assertEqual(make_settings(environment=SmarterEnvironments.LOCAL, api_schema="https").api_schema, "http")
        self.assertEqual(make_settings(environment=SmarterEnvironments.PROD, api_schema="HTTPS").api_schema, "https")
        with self.assertRaises(CONFIG_ERRORS):
            make_settings(environment=SmarterEnvironments.PROD, api_schema="ftp")


class TestSettingsReadyMessage(SmarterTestBase):
    """Test the message that Settings logs when it is created."""

    def test_ready_is_logged_once_per_server(self):
        """The first worker logs READY as a warning, so it is seen; the others log it at DEBUG."""
        with (
            patch.object(Settings, "ready", return_value=True),
            patch("smarter.common.conf.settings.is_first_worker", side_effect=[True, False]) as first,
            patch("smarter.common.conf.settings.logger") as logger,
        ):
            make_settings()
            make_settings()
        first.assert_called_with("settings-ready")
        ready = [c for c in logger.warning.call_args_list if "smarter_settings are" in c.args[0]]
        self.assertEqual(len(ready), 1)
        self.assertIn("READY", ready[0].args[2])
        self.assertEqual(len([c for c in logger.debug.call_args_list if "smarter_settings are" in str(c.args[0])]), 1)

    def test_not_ready_is_logged_by_every_process(self):
        """NOT_READY is always a warning, whichever worker logs it."""
        with (
            patch.object(Settings, "ready", return_value=False),
            patch("smarter.common.conf.settings.is_first_worker") as first,
            patch("smarter.common.conf.settings.logger") as logger,
        ):
            make_settings()
        first.assert_not_called()
        self.assertIn("NOT_READY", logger.warning.call_args.args[2])

    def test_the_prefix_is_not_red(self):
        """A healthy start doesn't look like an error."""
        with (
            patch.object(Settings, "ready", return_value=True),
            patch("smarter.common.conf.settings.is_first_worker", return_value=True),
            patch("smarter.common.conf.settings.logger") as logger,
        ):
            make_settings()
        self.assertEqual(logger.warning.call_args.kwargs["prefix_format"], SmarterFormattedText.LIGHT_GRAY)


class TestServiceType(SmarterTestBase):
    """The kind of pod (SERVICE_TYPE): validated, checked against what the settings see, and named when READY."""

    def test_valid_kinds(self):
        """A known kind is kept, trimmed and in lower case; empty is unknown; anything else is refused."""
        for kind in SmarterKubernetesPodKinds.all:
            if kind in SmarterKubernetesPodKinds.restricted:
                continue
            with self.subTest(kind=kind):
                self.assertEqual(make_settings(service_type=f" {kind.upper()} ").service_type, kind)
        self.assertIsNone(make_settings(service_type="").service_type)
        with self.assertRaises(CONFIG_ERRORS):
            make_settings(service_type="webserver")

    def test_restricted_kinds_match_the_settings(self):
        """The restricted workers are the pods without a database, and only the Extension worker takes its queue."""
        with as_restricted_worker():
            tool_worker = make_settings(service_type="worker-tools", database_unavailable=True)
            extension_worker = make_settings(
                service_type="worker-extensions",
                database_unavailable=True,
                app_tools_worker_queue="extensions_celery_task_queue",
            )
            with self.assertRaises(CONFIG_ERRORS):
                make_settings(service_type="api", database_unavailable=True)
            with self.assertRaises(CONFIG_ERRORS):
                make_settings(service_type="worker-extensions", database_unavailable=True)
        self.assertEqual(tool_worker.service_type, "worker-tools")
        self.assertTrue(extension_worker.is_extension_worker)
        with self.assertRaises(CONFIG_ERRORS):
            make_settings(service_type="worker-tools", database_unavailable=False)

    def test_the_ready_line_names_the_kind_and_its_checks(self):
        """READY names the kind of pod, or says that it is unknown, and the checks made for that kind."""
        with as_restricted_worker():
            tool_worker = make_settings(service_type="worker-tools", database_unavailable=True)
        self.assertEqual(tool_worker.pod_description(), "for the tool worker")
        self.assertEqual(tool_worker.readiness_checks(), ["it holds no credential but its own Redis password"])
        api = make_settings(service_type="api", environment=SmarterEnvironments.PROD)
        self.assertEqual(api.pod_description(), "for the api server")
        self.assertEqual(api.readiness_checks(), ["the root domain", "AWS credentials"])
        local = make_settings(service_type="api", environment=SmarterEnvironments.LOCAL)
        self.assertEqual(local.readiness_checks(), ["AWS credentials"])
        self.assertIn("SERVICE_TYPE is not set", make_settings(service_type="").pod_description())
        with (
            patch.object(Settings, "ready", return_value=True),
            patch("smarter.common.conf.settings.is_first_worker", return_value=True),
            patch("smarter.common.conf.settings.logger") as logger,
        ):
            make_settings(service_type="api", environment=SmarterEnvironments.PROD)
        arguments = logger.warning.call_args.args
        self.assertEqual(arguments[3:], ("for the api server", "the root domain, AWS credentials"))
        self.assertIn("(checked)", arguments[0])
