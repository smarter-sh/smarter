# -*- coding: utf-8 -*-
"""Django custom project settings"""

from smarter.common.conf import settings as smarter_settings


# SMARTER settings
SMARTER_ROOT_DOMAIN = smarter_settings.root_domain

SMARTER_CACHE_EXPIRATION = 600
SMARTER_API_SCHEMA = "http"

SMARTER_API_NAME = "Smarter API"
SMARTER_API_DESCRIPTION = "An enterprise class plugin-based AI chatbot platform"
SMARTER_API_VERSION = "v0"

SMARTER_BRANDING_CORPORATE_NAME = "Querium, Corporation"
SMARTER_BRANDING_SUPPORT_PHONE_NUMBER = "+1 (512) 833-6955"
SMARTER_BRANDING_SUPPORT_EMAIL = "support@querium.com"
SMARTER_BRANDING_ADDRESS = "1700 South Lamar Blvd, Suite 338, Austin, TX 78704"
SMARTER_BRANDING_CONTACT = "https://www.querium.com/contact/"
SMARTER_BRANDING_SUPPORT_HOURS = "9:00 AM - 5:00 PM GMT-6 (CST)"
SMARTER_BRANDING_URL_FACEBOOK = "https://www.facebook.com/Querium"
SMARTER_BRANDING_URL_TWITTER = "https://twitter.com/QueriumCorp"
SMARTER_BRANDING_URL_LINKEDIN = "https://www.linkedin.com/company/querium-corporation/"
