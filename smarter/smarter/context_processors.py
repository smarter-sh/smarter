# -*- coding: utf-8 -*-
# pylint: disable=W0613
"""Django context processors for base.html"""
from datetime import datetime

from django.conf import settings


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
