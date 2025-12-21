"""Django custom project settings"""

import re

from smarter.common.conf import bool_environment_variable
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SmarterEnvironments  # pylint: disable=W0611
from smarter.common.exceptions import SmarterConfigurationError  # pylint: disable=W0611


SMARTER_SETTINGS_OUTPUT = bool_environment_variable("SMARTER_SETTINGS_OUTPUT", False)
"""
If True, enables verbose output of Smarter run-time settings during Django startup.
This will generate a multi-line header in new terminal windows launched from
Kubernetes pods running Smarter services.
"""

# SMARTER platform settings
# -----------------------------------------------------------------------------
SMARTER_ROOT_DOMAIN = smarter_settings.root_domain
"""
Smarter root domain. This is not currently used.
"""

# Supplements to Django settings
# -----------------------------------------------------------------------------
SMARTER_ALLOWED_HOSTS = smarter_settings.allowed_hosts
"""
Supplemental list of allowed host/domain names for Smarter ChatBots/Agents.
This is specicific to Smarter and not officially part of Django settings.
"""

SMARTER_INTERNAL_IP_PREFIXES = smarter_settings.internal_ip_prefixes
"""
Supplemental list of internal IP prefixes used in smarter.apps.chatbot.middleware.security.SmarterSecurityMiddleware
and smarter.lib.django.middleware security features.

The default value is based on the default internal IP range used by Kubernetes clusters
by default unless otherwise configured.
"""


SMARTER_CACHE_EXPIRATION = smarter_settings.cache_expiration
"""
Default cache expiration time for Django views that use page caching.

See: django.views.decorators.cache.cache_control and django.views.decorators.cache.cache_page
"""

SMARTER_API_SCHEMA = smarter_settings.api_schema
"""
Smarter API schema (http or https).
"""

SMARTER_API_NAME = smarter_settings.api_name
"""
Name of the Smarter API. Not currently used.
"""

SMARTER_API_DESCRIPTION = smarter_settings.api_description
"""
Description of the Smarter API. Not currently used.
"""

# Marketing and branding settings
# -----------------------------------------------------------------------------
SMARTER_BRANDING_CORPORATE_NAME = smarter_settings.branding_corporate_name
"""
Smarter Branding. Provided to the Smarter web console dashboard
context processor for use in the common footer of html templates.
"""
SMARTER_BRANDING_SUPPORT_PHONE_NUMBER = smarter_settings.branding_support_phone_number
SMARTER_BRANDING_SUPPORT_EMAIL = smarter_settings.branding_support_email
SMARTER_BRANDING_ADDRESS = smarter_settings.branding_address
SMARTER_BRANDING_CONTACT_URL = smarter_settings.branding_contact_url
SMARTER_BRANDING_SUPPORT_HOURS = smarter_settings.branding_support_hours
SMARTER_BRANDING_URL_FACEBOOK = smarter_settings.branding_url_facebook
SMARTER_BRANDING_URL_TWITTER = smarter_settings.branding_url_twitter
SMARTER_BRANDING_URL_LINKEDIN = smarter_settings.branding_url_linkedin
SMARTER_EMAIL_ADMIN = smarter_settings.email_admin

# Chat settings
# -----------------------------------------------------------------------------
SMARTER_CHAT_CACHE_EXPIRATION = smarter_settings.chat_cache_expiration
"""
Default cache expiration time for chat message related views. Intended to
act as a mild deterrent against DDOS attacks.

see: :class:`smarter.apps.prompt.models.ChatHelper`
"""

# ChatBot settings
# -----------------------------------------------------------------------------
SMARTER_CHATBOT_CACHE_EXPIRATION = smarter_settings.chatbot_cache_expiration
"""
Default cache expiration time for ChatBot related views. Not currently used.
"""

SMARTER_CHATBOT_MAX_RETURNED_HISTORY = smarter_settings.chatbot_max_returned_history
"""
Maximum number of chat history messages to return in API responses. Not currently used.
"""

# Set these to true if we *DO NOT* place a wildcard A record in the customer API domain
# requiring that every chatbot have its own A record. This is the default behavior.
SMARTER_CHATBOT_TASKS_CREATE_DNS_RECORD = smarter_settings.chatbot_tasks_create_dns_record
"""
For programmatically creating DNS records in AWS Route53 during ChatBot deployment.
"""

# set this to true if we intend to create an ingress manifest for the customer API domain
# so that we can issue a certificate for it.
SMARTER_CHATBOT_TASKS_CREATE_INGRESS_MANIFEST = smarter_settings.chatbot_tasks_create_ingress_manifest
"""
For programmatically creating Kubernetes ingress manifests and TLS certificates for ChatBots during deployment.
"""

# For programmatically creating DNS records in AWS Route53.
# set the TTL for the DNS record.
SMARTER_CHATBOT_TASKS_DEFAULT_TTL = smarter_settings.chatbot_tasks_default_ttl
"""
Default TTL (time to live) for DNS records created in AWS Route53 during ChatBot deployment.
"""

# Celery worker task configuration
SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES = 3
"""
Maximum number of retries for Celery tasks related to ChatBot deployment and management.
"""

SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF = True
"""
If True, enables exponential backoff for Celery task retries related to ChatBot deployment and management
"""

SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE = "default_celery_task_queue"
"""
Name of the Celery task queue for ChatBot deployment and management tasks.
The default value should be sufficient for most deployments.
"""

# Plugin settings
SMARTER_PLUGIN_MAX_DATA_RESULTS = 50
"""
A global maximum number of data row results that can be returned by any
Smarter plugin. This is intended to act as a safeguard against
runaway queries that return massive result sets.
"""

SMARTER_SENSITIVE_FILES_AMNESTY_PATTERNS = [
    re.compile(r"^/dashboard/account/password-reset-link/[^/]+/[^/]+/$"),
    re.compile(r"^/api(/.*)?$"),
    re.compile(r"^/admin(/.*)?$"),
    re.compile(r"^/plugin(/.*)?$"),
    re.compile(r"^/docs/manifest(/.*)?$"),
    re.compile(r"^/docs/json-schema(/.*)?$"),
    re.compile(r".*stackademy.*"),
    re.compile(r"^/\.well-known/acme-challenge(/.*)?$"),
]
"""
Sensitive file amnesty patterns used by smarter.lib.django.middleware.sensitive_files.SensitiveFileAccessMiddleware.
Requests matching these patterns will be allowed even if they match sensitive file names.

Do not modify this setting unless you fully understand the implications of doing so.
"""
