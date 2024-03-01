# -*- coding: utf-8 -*-
"""Django context processors for base.html"""
from datetime import datetime
from urllib.parse import urljoin

from smarter.__version__ import __version__
from smarter.apps.account.models import Account, UserProfile
from smarter.apps.chat.models import ChatHistory


def base(request):
    """
    Base context processor for all templates that inherit
    from base.html, which renders the dashboard layout
    """
    current_year = datetime.now().year
    base_keys = {
        "smarter_version": __version__,
        "footer_message": f"Copyright {current_year}. All rights reserved.",
    }
    if request.user.is_authenticated:
        user_profile = UserProfile.objects.get(user=request.user)
        account = Account.objects.get(id=user_profile.account_id)
        user_keys = {
            "user_name": request.user.username,
            "user_first_name": request.user.first_name,
            "user_last_name": request.user.last_name,
            "user_email": request.user.email,
            "my_plugins": 12,
            "django_admin_title": "Account Administration - " + account.company_name,
        }
        return {**base_keys, **user_keys}
    return base_keys


def react(request):
    """
    React context processor for all templates that render
    a React app.
    """
    chat_history = ChatHistory.objects.filter(user=request.user).order_by("-created_at").first()
    chat_id = chat_history.chat_id if chat_history else "undefined"
    messages = chat_history.messages if chat_history else []
    most_recent_response = chat_history.response if chat_history else None

    base_url = f"{request.scheme}://{request.get_host()}/"
    api_url = urljoin(base_url, "/api/v0/")
    context_prefix = "BACKEND_"
    return {
        "react": True,
        "react_config": {
            context_prefix + "BASE_URL": base_url,
            context_prefix + "API_URL": api_url,
            context_prefix + "CHAT_ID": chat_id,
            context_prefix + "CHAT_HISTORY": messages,
            context_prefix + "CHAT_MOST_RECENT_RESPONSE": most_recent_response,
        },
    }
