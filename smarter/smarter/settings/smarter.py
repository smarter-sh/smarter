"""Django custom project settings"""

from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SmarterEnvironments  # pylint: disable=W0611
from smarter.common.exceptions import SmarterConfigurationError  # pylint: disable=W0611


# SMARTER platform settings
# -----------------------------------------------------------------------------
SMARTER_ROOT_DOMAIN = smarter_settings.root_domain
SMARTER_CACHE_EXPIRATION = 60 * 5  # 5 minutes
SMARTER_API_SCHEMA = "http"
SMARTER_API_NAME = "Smarter API"
SMARTER_API_DESCRIPTION = "An enterprise class plugin-based AI chatbot platform"

# Marketing and branding settings
# -----------------------------------------------------------------------------
SMARTER_BRANDING_CORPORATE_NAME = "Querium, Corporation"
SMARTER_BRANDING_SUPPORT_PHONE_NUMBER = "+1 (512) 833-6955"
SMARTER_BRANDING_SUPPORT_EMAIL = "support@querium.com"
SMARTER_BRANDING_ADDRESS = "1700 South Lamar Blvd, Suite 338, Austin, TX 78704"
SMARTER_BRANDING_CONTACT = "https://www.querium.com/contact/"
SMARTER_BRANDING_SUPPORT_HOURS = "MON-FRI 9:00 AM - 5:00 PM GMT-6 (CST)"
SMARTER_BRANDING_URL_FACEBOOK = "https://www.facebook.com/Querium"
SMARTER_BRANDING_URL_TWITTER = "https://twitter.com/QueriumCorp"
SMARTER_BRANDING_URL_LINKEDIN = "https://www.linkedin.com/company/querium-corporation/"
SMARTER_EMAIL_ADMIN = "lawrence@querium.com"

# Chat settings
# -----------------------------------------------------------------------------
SMARTER_CHAT_CACHE_EXPIRATION = 60 * 5  # 5 minutes

# ChatBot settings
# -----------------------------------------------------------------------------
SMARTER_CHATBOT_CACHE_EXPIRATION = 60 * 5  # 5 minutes
SMARTER_CHATBOT_MAX_RETURNED_HISTORY = 25

# Set these to true if we *DO NOT* place a wildcard A record in the customer API domain
# requiring that every chatbot have its own A record. This is the default behavior.
SMARTER_CHATBOT_TASKS_CREATE_DNS_RECORD = True

# set this to true if we intend to create an ingress manifest for the customer API domain
# so that we can issue a certificate for it.
SMARTER_CHATBOT_TASKS_CREATE_INGRESS_MANIFEST = True

# For programmatically creating DNS records in AWS Route53.
# set the TTL for the DNS record.
SMARTER_CHATBOT_TASKS_DEFAULT_TTL = 600

# Celery worker task configuration
SMARTER_CHATBOT_TASKS_CELERY_MAX_RETRIES = 3
SMARTER_CHATBOT_TASKS_CELERY_RETRY_BACKOFF = True
SMARTER_CHATBOT_TASKS_CELERY_TASK_QUEUE = "default_celery_task_queue"

# Plugin settings
SMARTER_PLUGIN_MAX_DATA_RESULTS = 50
