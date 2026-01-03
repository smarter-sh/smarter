# pylint: disable=wrong-import-position
"""
Test configuration Settings class.
"""

import logging
import re

# 3rd party stuff
from pydantic import SecretStr

# our stuff
from smarter.common.conf import settings as smarter_settings
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.unittest.base_classes import SmarterTestBase


logger = logging.getLogger(__name__)


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

    smarter_test_base_logger_prefix = formatted_text(f"{__name__}.TestSettings()")

    @classmethod
    def setUpClass(cls):
        """Set up class by loading environment variables."""
        super().setUpClass()
        logger.info("%s.setUpClass()", cls.smarter_test_base_logger_prefix)
        cls.smarter_settings = smarter_settings

        logger.info(
            "%s.setUpClass(): Testing environment %s",
            cls.smarter_test_base_logger_prefix,
            smarter_settings.environment,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        """Tear down the test class."""
        logger.info("%s.tearDownClass()", cls.smarter_test_base_logger_prefix)
        super().tearDownClass()

    ###########################################################################
    # Pydantic BaseSettings fields tests
    ###########################################################################
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

    def test_another_training_example(self):
        self.assertIsNotNone(smarter_settings.anthropic_api_key)
        self.assertIsInstance(smarter_settings.anthropic_api_key, SecretStr)

    def test_api_description(self):
        self.assertIsNotNone(smarter_settings.api_description)

    def test_api_name(self):
        self.assertIsNotNone(smarter_settings.api_name)

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

    def test_aws_region(self):
        self.assertIsNotNone(smarter_settings.aws_region)

    def test_aws_eks_cluster_name(self):
        self.assertIsNotNone(smarter_settings.aws_eks_cluster_name)

    def test_aws_db_instance_identifier(self):
        self.assertIsNotNone(smarter_settings.aws_db_instance_identifier)

    def test_branding_corporate_name(self):
        self.assertIsNotNone(smarter_settings.branding_corporate_name)

    def test_branding_support_phone_number(self):
        self.assertIsNotNone(smarter_settings.branding_support_phone_number)

    def test_branding_support_email(self):
        self.assertIsNotNone(smarter_settings.branding_support_email)

    def test_branding_address(self):
        self.assertIsNotNone(smarter_settings.branding_address)

    def test_branding_contact_url(self):
        self.assertIsNotNone(smarter_settings.branding_contact_url)

    def test_branding_support_hours(self):
        self.assertIsNotNone(smarter_settings.branding_support_hours)

    def test_branding_url_facebook(self):
        self.assertIsNotNone(smarter_settings.branding_url_facebook)

    def test_branding_url_twitter(self):
        self.assertIsNotNone(smarter_settings.branding_url_twitter)

    def test_branding_url_linkedin(self):
        self.assertIsNotNone(smarter_settings.branding_url_linkedin)

    def test_cache_expiration(self):
        self.assertIsNotNone(smarter_settings.cache_expiration)

    def test_chat_cache_expiration(self):
        self.assertIsNotNone(smarter_settings.chat_cache_expiration)

    def test_chatbot_cache_expiration(self):
        self.assertIsNotNone(smarter_settings.chatbot_cache_expiration)

    def test_chatbot_max_returned_history(self):
        self.assertIsNotNone(smarter_settings.chatbot_max_returned_history)

    def test_chatbot_tasks_create_dns_record(self):
        self.assertIsNotNone(smarter_settings.chatbot_tasks_create_dns_record)

    def test_chatbot_tasks_create_ingress_manifest(self):
        self.assertIsNotNone(smarter_settings.chatbot_tasks_create_ingress_manifest)

    def test_chatbot_tasks_default_ttl(self):
        self.assertIsNotNone(smarter_settings.chatbot_tasks_default_ttl)

    def test_chatbot_tasks_celery_max_retries(self):
        self.assertIsNotNone(smarter_settings.chatbot_tasks_celery_max_retries)

    def test_chatbot_tasks_celery_retry_backoff(self):
        self.assertIsNotNone(smarter_settings.chatbot_tasks_celery_retry_backoff)

    def test_chatbot_tasks_celery_task_queue(self):
        self.assertIsNotNone(smarter_settings.chatbot_tasks_celery_task_queue)

    def test_plugin_max_data_results(self):
        self.assertIsNotNone(smarter_settings.plugin_max_data_results)

    def test_sensitive_files_amnesty_patterns(self):
        self.assertIsNotNone(smarter_settings.sensitive_files_amnesty_patterns)

    def test_debug_mode(self):
        self.assertIsNotNone(smarter_settings.debug_mode)

    def test_dump_defaults(self):
        self.assertIsNotNone(smarter_settings.dump_defaults)

    def test_default_missing_value(self):
        self.assertIsNotNone(smarter_settings.default_missing_value)

    def test_developer_mode(self):
        self.assertIsNotNone(smarter_settings.developer_mode)

    def test_django_default_file_storage(self):
        self.assertIsNotNone(smarter_settings.django_default_file_storage)

    def test_email_admin(self):
        self.assertIsNotNone(smarter_settings.email_admin)

    def test_environment(self):
        self.assertIsNotNone(smarter_settings.environment)

    def test_fernet_encryption_key(self):
        self.assertIsNotNone(smarter_settings.fernet_encryption_key)

    def test_gemini_api_key(self):
        self.assertIsNotNone(smarter_settings.gemini_api_key)

    def test_google_maps_api_key(self):
        self.assertIsNotNone(smarter_settings.google_maps_api_key)

    def test_google_service_account(self):
        self.assertIsNotNone(smarter_settings.google_service_account)

    def test_internal_ip_prefixes(self):
        self.assertIsNotNone(smarter_settings.internal_ip_prefixes)

    def test_log_level(self):
        self.assertIsNotNone(smarter_settings.log_level)

    def test_llama_api_key(self):
        self.assertIsNotNone(smarter_settings.llama_api_key)

    def test_local_hosts(self):
        self.assertIsNotNone(smarter_settings.local_hosts)

    def test_langchain_memory_key(self):
        self.assertIsNotNone(smarter_settings.langchain_memory_key)

    def test_llm_default_provider(self):
        self.assertIsNotNone(smarter_settings.llm_default_provider)

    def test_llm_default_model(self):
        self.assertIsNotNone(smarter_settings.llm_default_model)

    def test_llm_default_system_role(self):
        self.assertIsNotNone(smarter_settings.llm_default_system_role)

    def test_llm_default_temperature(self):
        self.assertIsNotNone(smarter_settings.llm_default_temperature)

    def test_llm_default_max_tokens(self):
        self.assertIsNotNone(smarter_settings.llm_default_max_tokens)

    def test_logo(self):
        self.assertIsNotNone(smarter_settings.logo)

    def test_mailchimp_api_key(self):
        self.assertIsNotNone(smarter_settings.mailchimp_api_key)

    def test_mailchimp_list_id(self):
        self.assertIsNotNone(smarter_settings.mailchimp_list_id)

    def test_marketing_site_url(self):
        self.assertIsNotNone(smarter_settings.marketing_site_url)

    def test_openai_api_organization(self):
        self.assertIsNotNone(smarter_settings.openai_api_organization)

    def test_openai_api_key(self):
        self.assertIsNotNone(smarter_settings.openai_api_key)

    def test_openai_endpoint_image_n(self):
        self.assertIsNotNone(smarter_settings.openai_endpoint_image_n)

    def test_openai_endpoint_image_size(self):
        self.assertIsNotNone(smarter_settings.openai_endpoint_image_size)

    def test_pinecone_api_key(self):
        self.assertIsNotNone(smarter_settings.pinecone_api_key)

    def test_root_domain(self):
        self.assertIsNotNone(smarter_settings.root_domain)

    def test_secret_key(self):
        self.assertIsNotNone(smarter_settings.secret_key)

    def test_settings_output(self):
        self.assertIsNotNone(smarter_settings.settings_output)

    def test_shared_resource_identifier(self):
        self.assertIsNotNone(smarter_settings.shared_resource_identifier)

    def test_smarter_mysql_test_database_secret_name(self):
        self.assertIsNotNone(smarter_settings.smarter_mysql_test_database_secret_name)

    def test_smarter_mysql_test_database_password(self):
        self.assertIsNotNone(smarter_settings.smarter_mysql_test_database_password)

    def test_smarter_reactjs_app_loader_path(self):
        self.assertIsNotNone(smarter_settings.smarter_reactjs_app_loader_path)

    def test_social_auth_google_oauth2_key(self):
        self.assertIsNotNone(smarter_settings.social_auth_google_oauth2_key)

    def test_social_auth_google_oauth2_secret(self):
        self.assertIsNotNone(smarter_settings.social_auth_google_oauth2_secret)

    def test_social_auth_github_key(self):
        self.assertIsNotNone(smarter_settings.social_auth_github_key)

    def test_social_auth_github_secret(self):
        self.assertIsNotNone(smarter_settings.social_auth_github_secret)

    def test_social_auth_linkedin_oauth2_key(self):
        # deprecated, no longer used
        pass

    def test_social_auth_linkedin_oauth2_secret(self):
        # deprecated, no longer used
        pass

    def test_smtp_sender(self):
        self.assertIsNotNone(smarter_settings.smtp_sender)

    def test_smtp_from_email(self):
        self.assertIsNotNone(smarter_settings.smtp_from_email)

    def test_smtp_host(self):
        self.assertIsNotNone(smarter_settings.smtp_host)

    def test_smtp_password(self):
        self.assertIsNotNone(smarter_settings.smtp_password)

    def test_smtp_port(self):
        self.assertIsNotNone(smarter_settings.smtp_port)

    def test_smtp_use_ssl(self):
        self.assertIsNotNone(smarter_settings.smtp_use_ssl)

    def test_smtp_use_tls(self):
        self.assertIsNotNone(smarter_settings.smtp_use_tls)

    def test_smtp_username(self):
        self.assertIsNotNone(smarter_settings.smtp_username)

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

    def test_smarter_api_key_max_lifetime_days_property(self):
        self.assertIsNotNone(smarter_settings.smarter_api_key_max_lifetime_days)

    def test_smarter_reactjs_app_loader_url_property(self):
        self.assertIsNotNone(smarter_settings.smarter_reactjs_app_loader_url)

    def test_smarter_reactjs_root_div_id_property(self):
        self.assertIsNotNone(smarter_settings.smarter_reactjs_root_div_id)

    def test_version_property(self):
        self.assertIsNotNone(smarter_settings.version)
