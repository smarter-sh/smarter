# pylint: disable=W0613
"""Django context processors for base.html"""
import time
from datetime import datetime

from django.conf import settings

from smarter.__version__ import __version__


def base(request):
    """
    Base context processor for all templates that inherit
    from base.html, which renders the dashboard layout
    """
    current_year = datetime.now().year
    context = {
        "dashboard": {
            "product_name": "Smarter",
            "company_name": "Querium, Corp",
            "smarter_version": __version__,
            "current_year": current_year,
            "product_description": "Smarter is an enterprise class plugin-based chat solution.",
        }
    }
    return context


def branding(request):
    """
    Branding context processor for all templates that inherit
    from base.html, which renders the dashboard layout
    """
    current_year = datetime.now().year
    root_url = request.build_absolute_uri("/").rstrip("/")
    context = {
        "branding": {
            "root_url": root_url,
            "support_phone_number": settings.SMARTER_BRANDING_SUPPORT_PHONE_NUMBER,
            "corporate_name": settings.SMARTER_BRANDING_CORPORATE_NAME,
            "support_email": settings.SMARTER_BRANDING_SUPPORT_EMAIL,
            "corp_address": settings.SMARTER_BRANDING_ADDRESS,
            "contact": settings.SMARTER_BRANDING_CONTACT,
            "support_hours": settings.SMARTER_BRANDING_SUPPORT_HOURS,
            "copy_right": f"© {current_year} {settings.SMARTER_BRANDING_CORPORATE_NAME}. All rights reserved.",
            "url_facebook": settings.SMARTER_BRANDING_URL_FACEBOOK,
            "url_twitter": settings.SMARTER_BRANDING_URL_TWITTER,
            "url_linkedin": settings.SMARTER_BRANDING_URL_LINKEDIN,
        }
    }
    return context


def cache_buster(request):
    """For local development, prevent browser caching of static assets."""
    return {"cache_buster": "v=" + str(time.time())}
