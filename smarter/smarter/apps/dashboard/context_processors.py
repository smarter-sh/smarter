# -*- coding: utf-8 -*-
# pylint: disable=W0613
"""Django context processors for base.html"""
from datetime import datetime
from urllib.parse import urljoin

from django.conf import settings

from smarter.__version__ import __version__
from smarter.apps.chat.models import ChatHistory


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
            "footer_message": f"Copyright {current_year}. All rights reserved.",
        }
    }
    return context


def react(request):
    """
    React context processor for all templates that render
    a React app.
    """
    chat_history = ChatHistory.objects.filter(user=request.user).order_by("-created_at").first()
    chat_id = chat_history.chat_id if chat_history else "undefined"
    messages = chat_history.messages if chat_history else []
    most_recent_response = chat_history.response if chat_history else None

    base_url = f"{settings.SMARTER_API_SCHEMA}://{request.get_host()}/"
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
