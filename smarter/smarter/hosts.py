"""
Django Hosts configuration.
"""

from django_hosts import host, patterns

from smarter.common.const import SMARTER_API_SUBDOMAIN, SMARTER_PLATFORM_SUBDOMAIN


host_patterns = patterns(
    "",
    host(
        rf"{SMARTER_PLATFORM_SUBDOMAIN}", "smarter.urls", name=SMARTER_PLATFORM_SUBDOMAIN
    ),  # for https://platform.smarter.sh/
    host(
        rf"{SMARTER_API_SUBDOMAIN}", "smarter.urls_api", name=SMARTER_API_SUBDOMAIN
    ),  # for https://api.platform.smarter.sh/
)
