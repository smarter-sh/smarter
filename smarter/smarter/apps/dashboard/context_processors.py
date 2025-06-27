# pylint: disable=W0613
"""Django context processors for base.html"""
import time
from datetime import datetime
from typing import Optional

from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest

from smarter.__version__ import __version__
from smarter.apps.account.models import User, get_resolved_user
from smarter.apps.account.utils import get_cached_account_for_user
from smarter.apps.chatbot.models import ChatBot, ChatBotAPIKey, ChatBotCustomDomain
from smarter.apps.plugin.models import PluginMeta
from smarter.lib.cache import cache_results


CACHE_TIMEOUT = 60  # 1 minute


@cache_results(timeout=CACHE_TIMEOUT)
def get_pending_deployments(user: User) -> int:
    """
    Get the number of pending deployments for the current user
    """
    account = get_cached_account_for_user(user)
    return ChatBot.objects.filter(account=account, deployed=False).count() or 0


@cache_results(timeout=CACHE_TIMEOUT)
def get_chatbots(user: User) -> int:
    """
    Get the number of chatbots for the current user
    """
    account = get_cached_account_for_user(user)
    return ChatBot.objects.filter(account=account).count() or 0


@cache_results(timeout=CACHE_TIMEOUT)
def get_plugins(user: User) -> int:
    """
    Get the number of plugins for the current user
    """
    account = get_cached_account_for_user(user)
    return PluginMeta.objects.filter(account=account).count() or 0


@cache_results(timeout=CACHE_TIMEOUT)
def get_api_keys(user: User) -> int:
    """
    Get the number of API keys for the current user
    """
    account = get_cached_account_for_user(user)
    return ChatBotAPIKey.objects.filter(chatbot__account=account).count() or 0


@cache_results(timeout=CACHE_TIMEOUT)
def get_custom_domains(user: User) -> int:
    """
    Get the number of custom domains for the current user
    """
    account = get_cached_account_for_user(user)
    return ChatBotCustomDomain.objects.filter(chatbot__account=account).count() or 0


def base(request: WSGIRequest) -> dict:
    """
    Base context processor for all templates that inherit
    from base.html, which renders the dashboard layout
    """
    user = request.user
    resolved_user = get_resolved_user(user)

    @cache_results(timeout=CACHE_TIMEOUT)
    def get_cached_context(user: Optional[User]) -> dict:
        current_year = datetime.now().year
        user_email = "anonymous@mail.edu"
        username = "anonymous"
        is_superuser = False
        is_staff = False
        if user and user.is_authenticated:
            try:
                user_email = user.email
                username = user.username
                is_superuser = user.is_superuser
                is_staff = user.is_staff
            except AttributeError:
                pass

        cached_context = {
            "dashboard": {
                "user_email": user_email,
                "username": username,
                "is_superuser": is_superuser,
                "is_staff": is_staff,
                "product_name": "Smarter",
                "company_name": "Querium, Corp",
                "smarter_version": "v" + __version__,
                "current_year": current_year,
                "product_description": "Smarter is an enterprise class plugin-based chat solution.",
                "my_resources_pending_deployments": get_pending_deployments(user=resolved_user) if resolved_user else 0,
                "my_resources_chatbots": get_chatbots(user=resolved_user) if resolved_user else 0,
                "my_resources_plugins": get_plugins(user=resolved_user) if resolved_user else 0,
                "my_resources_api_keys": get_api_keys(user=resolved_user) if resolved_user else 0,
                "my_resources_custom_domains": get_custom_domains(user=resolved_user) if resolved_user else 0,
            }
        }
        return cached_context

    context = get_cached_context(user=resolved_user)
    return context


def branding(request: WSGIRequest) -> dict:
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


def cache_buster(request) -> dict:
    """For local development, prevent browser caching of static assets."""
    return {"cache_buster": "v=" + str(time.time())}
