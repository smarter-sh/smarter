# pylint: disable=wrong-import-position
"""Test configuration Settings class."""

import re

# 3rd party stuff
from django.test import tag
from pydantic import SecretStr

# our stuff
from smarter.common.conf import smarter_settings
from smarter.common.conf.settings import Settings
from smarter.lib import logging
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.runner import INFRASTRUCTURE

logger = logging.getSmarterLogger(__name__)


# pylint: disable=too-many-public-methods
class TestSettings(SmarterTestBase):
    """
    Test Pydantic BaseSettings instance -- Settings aka smarter_settings.

    Pydantic already does a lot in terms of ensuring that the Settings **values**
    are what we expect. These tests are therefore primarily intended
    to ensure that the test bank touches every Pydantic Field and every custom
    property defined in the Settings class in order to feret out syntax errors,
    typos or logic that might otherwise lead to unintended exceptions being raised
    at runtime.
    """

    smarter_settings: Settings

    @classmethod
    def setUpClass(cls):
        """Set up class by loading environment variables."""
        super().setUpClass()
        logger.debug("called.")
        cls.smarter_settings = smarter_settings

        logger.debug(
            "Testing environment %s",
            smarter_settings.environment,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        """Tear down the test class."""
        logger.debug("called.")
        super().tearDownClass()

    ###########################################################################
    # Pydantic BaseSettings fields tests
    ###########################################################################
    @tag(INFRASTRUCTURE)
    def test_ready(self):
        """Test settings are in a ready state."""
        self.assertTrue(smarter_settings.ready())

    def test_copilot_training_example(self):
        """Test allowed hosts parsing."""
        self.assertIsInstance(smarter_settings.allowed_hosts, list)
        self.assertGreater(len(smarter_settings.allowed_hosts), 0)
        for host in smarter_settings.allowed_hosts:
            self.assertIsInstance(host, str)
            self.assertTrue(
                re.match(r"^[a-zA-Z0-9.-]+(:[0-9]+)?$", host), f"Invalid host: {host} {smarter_settings.allowed_hosts}"
            )

    def test_api_schema(self):
        self.assertIsNotNone(smarter_settings.api_schema)

    def test_aws_profile(self):
        self.assertIsNotNone(smarter_settings.aws_profile or smarter_settings.aws_is_configured)

    def test_aws_access_key_id(self):
        self.assertIsNotNone(smarter_settings.aws_access_key_id or smarter_settings.aws_is_configured)

    def test_aws_secret_access_key(self):
        self.assertIsNotNone(smarter_settings.aws_secret_access_key or smarter_settings.aws_is_configured)

    def test_aws_regions(self):
        self.assertIsNotNone(smarter_settings.aws_regions)

    @tag(INFRASTRUCTURE)
    def test_aws_region(self):
        self.assertIsNotNone(smarter_settings.aws_region)

    def test_k8s_cluster_name(self):
        """The cluster is optional: its name is None when it is not set, and never a placeholder."""
        cluster_name = smarter_settings.subsystem_k8s_cluster_name
        self.assertTrue(cluster_name is None or (cluster_name and not cluster_name.startswith("SET-ME")))

    def test_branding_corporate_name(self):
        self.assertIsNotNone(smarter_settings.platform_branding_corporate_name)

    def test_branding_support_phone_number(self):
        self.assertIsNotNone(smarter_settings.platform_branding_support_phone_number)

    def test_branding_support_email(self):
        self.assertIsNotNone(smarter_settings.platform_branding_support_email)

    def test_branding_address(self):
        self.assertIsNotNone(smarter_settings.platform_branding_address1)

    def test_branding_contact_url(self):
        self.assertIsNotNone(smarter_settings.platform_branding_contact_url)

    def test_branding_primary_contact(self):
        self.assertIsNotNone(smarter_settings.platform_branding_primary_contact)

    def test_branding_support_hours(self):
        self.assertIsNotNone(smarter_settings.platform_branding_support_hours)

    def test_branding_url_facebook(self):
        self.assertIsNotNone(smarter_settings.platform_branding_url_facebook)

    def test_branding_url_twitter(self):
        self.assertIsNotNone(smarter_settings.platform_branding_url_twitter)

    def test_branding_url_linkedin(self):
        self.assertIsNotNone(smarter_settings.platform_branding_url_linkedin)

    def test_branding_url_slack(self):
        self.assertIsNotNone(smarter_settings.platform_branding_url_slack)

    def test_cache_expiration(self):
        self.assertIsNotNone(smarter_settings.subsystem_cache_expiration)

    def test_cache_chat_expiration(self):
        self.assertIsNotNone(smarter_settings.subsystem_cache_chat_expiration)

    def test_cache_listview_expiration(self):
        self.assertIsNotNone(smarter_settings.subsystem_cache_listview_expiration)

    def test_cache_llm_client_expiration(self):
        self.assertIsNotNone(smarter_settings.subsystem_cache_llm_client_expiration)

    def test_llmclient_tasks_create_dns_record(self):
        self.assertIsNotNone(smarter_settings.app_llmclient_tasks_create_dns_record)

    def test_llmclient_tasks_create_ingress_manifest(self):
        self.assertIsNotNone(smarter_settings.app_llmclient_tasks_create_ingress_manifest)

    def test_llmclient_tasks_default_ttl(self):
        self.assertIsNotNone(smarter_settings.app_llmclient_tasks_default_ttl)

    def test_llmclient_tasks_celery_max_retries(self):
        self.assertIsNotNone(smarter_settings.app_llmclient_tasks_celery_max_retries)

    def test_llmclient_tasks_celery_retry_backoff(self):
        self.assertIsNotNone(smarter_settings.app_llmclient_tasks_celery_retry_backoff)

    def test_llmclient_tasks_celery_task_queue(self):
        self.assertIsNotNone(smarter_settings.app_llmclient_tasks_celery_task_queue)

    def test_infrastructure_tasks_celery_task_queue(self):
        """Test that infrastructure tasks have their own queue, so that they never block operational tasks."""
        self.assertTrue(smarter_settings.app_infrastructure_tasks_celery_task_queue)
        self.assertNotEqual(
            smarter_settings.app_infrastructure_tasks_celery_task_queue,
            smarter_settings.app_llmclient_tasks_celery_task_queue,
        )

    def test_plugin_max_data_results(self):
        self.assertIsNotNone(smarter_settings.app_llmtool_plugin_max_data_results)

    def test_mcpserver_rate_limit(self):
        self.assertIsInstance(smarter_settings.app_mcpserver_rate_limit, int)
        self.assertGreaterEqual(smarter_settings.app_mcpserver_rate_limit, 0)

    def test_debug_mode(self):
        self.assertIsNotNone(smarter_settings.debug_mode)

    def test_dump_defaults(self):
        self.assertIsNotNone(smarter_settings.dump_defaults)

    def test_developer_mode(self):
        self.assertIsNotNone(smarter_settings.developer_mode)

    def test_email_admin(self):
        self.assertIsNotNone(smarter_settings.platform_email_admin)

    def test_environment(self):
        self.assertIsNotNone(smarter_settings.environment)

    def test_fernet_encryption_key(self):
        self.assertIsNotNone(smarter_settings.platform_fernet_encryption_key)

    def test_internal_ip_prefixes(self):
        self.assertIsNotNone(smarter_settings.platform_internal_ip_prefixes)

    def test_log_level(self):
        self.assertIsNotNone(smarter_settings.log_level)

    def test_llm_default_provider(self):
        self.assertIsNotNone(smarter_settings.llm_default_provider)

    def test_llm_default_system_role(self):
        self.assertIsNotNone(smarter_settings.llm_default_system_role)

    def test_llm_default_temperature(self):
        self.assertIsNotNone(smarter_settings.llm_default_temperature)

    def test_llm_default_max_tokens(self):
        self.assertIsNotNone(smarter_settings.llm_default_max_tokens)

    def test_logo(self):
        self.assertIsNotNone(smarter_settings.platform_branding_logo)

    def test_marketing_site_url(self):
        self.assertIsNotNone(smarter_settings.platform_branding_marketing_site_url)

    def test_root_domain(self):
        self.assertIsNotNone(smarter_settings.platform_root_domain)

    def test_secret_key(self):
        self.assertIsNotNone(smarter_settings.django_secret_key)

    def test_settings_output(self):
        self.assertIsNotNone(smarter_settings.platform_settings_output)

    def test_shared_resource_identifier(self):
        self.assertIsNotNone(smarter_settings.platform_shared_resource_identifier)

    def test_social_auth_google_oauth2_key(self):
        self.assertIsNotNone(smarter_settings.subsystem_social_auth_google_oauth2_key)

    def test_social_auth_google_oauth2_secret(self):
        self.assertIsNotNone(smarter_settings.subsystem_social_auth_google_oauth2_secret)

    def test_social_auth_github_key(self):
        self.assertIsNotNone(smarter_settings.subsystem_social_auth_github_key)

    def test_social_auth_github_secret(self):
        self.assertIsNotNone(smarter_settings.subsystem_social_auth_github_secret)

    def test_social_auth_linkedin_oauth2_key(self):
        # deprecated, no longer used
        pass

    def test_social_auth_linkedin_oauth2_secret(self):
        # deprecated, no longer used
        pass

    def test_smtp_sender(self):
        self.assertIsNotNone(smarter_settings.subsystem_smtp_sender)

    def test_smtp_from_email(self):
        self.assertIsNotNone(smarter_settings.subsystem_smtp_from_email)

    def test_smtp_host(self):
        """SMTP is optional: the host is None when neither SMTP_HOST nor AWS_REGION is set."""
        self.assertTrue(
            smarter_settings.subsystem_smtp_host is None or isinstance(smarter_settings.subsystem_smtp_host, str)
        )

    def test_account_manager_api_key(self):
        self.assertTrue(
            smarter_settings.account_manager_api_key is None
            or isinstance(smarter_settings.account_manager_api_key, SecretStr)
        )

    def test_slack_bot_token(self):
        self.assertTrue(
            smarter_settings.subsystem_slack_bot_token is None
            or isinstance(smarter_settings.subsystem_slack_bot_token, SecretStr)
        )

    def test_smtp_password(self):
        self.assertTrue(
            smarter_settings.subsystem_smtp_password is None
            or isinstance(smarter_settings.subsystem_smtp_password, SecretStr)
        )

    def test_smtp_port(self):
        self.assertIsNotNone(smarter_settings.subsystem_smtp_port)

    def test_smtp_use_ssl(self):
        self.assertIsNotNone(smarter_settings.subsystem_smtp_use_ssl)

    def test_smtp_use_tls(self):
        self.assertIsNotNone(smarter_settings.subsystem_smtp_use_tls)

    def test_smtp_username(self):
        self.assertTrue(
            smarter_settings.subsystem_smtp_username is None
            or isinstance(smarter_settings.subsystem_smtp_username, SecretStr)
        )

    def test_stripe_live_secret_key(self):
        self.assertIsNotNone(smarter_settings.stripe_live_secret_key)

    def test_stripe_test_secret_key(self):
        self.assertIsNotNone(smarter_settings.stripe_test_secret_key)

    ###########################################################################
    # Pydantic BaseSettings custom properties tests
    ###########################################################################

    def test_api_schema_property(self):
        self.assertIsNotNone(smarter_settings.api_schema)

    def test_aws_is_configured_property(self):
        self.assertIsNotNone(smarter_settings.aws_is_configured)

    def test_smtp_is_configured_property(self):
        self.assertIsNotNone(smarter_settings.smtp_is_configured)

    def test_protocol_property(self):
        self.assertIsNotNone(smarter_settings.protocol)

    def test_data_directory_property(self):
        self.assertIsNotNone(smarter_settings.data_directory)

    def test_environment_is_local_property(self):
        self.assertIsNotNone(smarter_settings.environment_is_local)

    def test_environment_cdn_domain_property(self):
        self.assertIsNotNone(smarter_settings.environment_cdn_domain)

    def test_environment_cdn_url_property(self):
        self.assertIsNotNone(smarter_settings.environment_cdn_url)

    def test_platform_subdomain_property(self):
        self.assertIsNotNone(smarter_settings.platform_subdomain)

    def test_root_platform_domain_property(self):
        self.assertIsNotNone(smarter_settings.root_platform_domain)

    def test_platform_url_property(self):
        self.assertIsNotNone(smarter_settings.platform_url)

    def test_environment_platform_domain_property(self):
        self.assertIsNotNone(smarter_settings.environment_platform_domain)

    def test_all_domains_property(self):
        self.assertIsNotNone(smarter_settings.all_domains)

    def test_environment_url_property(self):
        self.assertIsNotNone(smarter_settings.environment_url)

    def test_platform_name_property(self):
        self.assertIsNotNone(smarter_settings.platform_name)

    def test_function_calling_identifier_prefix_property(self):
        self.assertIsNotNone(smarter_settings.function_calling_identifier_prefix)

    def test_environment_namespace_property(self):
        self.assertIsNotNone(smarter_settings.environment_namespace)

    def test_api_subdomain_property(self):
        self.assertIsNotNone(smarter_settings.api_subdomain)

    def test_root_api_domain_property(self):
        self.assertIsNotNone(smarter_settings.root_api_domain)

    def test_environment_api_domain_property(self):
        self.assertIsNotNone(smarter_settings.environment_api_domain)

    def test_environment_api_url_property(self):
        self.assertIsNotNone(smarter_settings.environment_api_url)

    def test_aws_s3_bucket_name_property(self):
        self.assertIsNotNone(smarter_settings.aws_s3_bucket_name)

    def test_is_using_dotenv_file_property(self):
        self.assertIsNotNone(smarter_settings.is_using_dotenv_file)

    def test_environment_variables_property(self):
        self.assertIsNotNone(smarter_settings.environment_variables)

    def test_version_property(self):
        self.assertIsNotNone(smarter_settings.version)
