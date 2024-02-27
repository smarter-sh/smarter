# -*- coding: utf-8 -*-
"""Django context processors for base.html"""
from smarter.__version__ import __version__


def base(request):
    return {
        "user_name": request.user.username if request.user.is_authenticated else "Guest",
        "user_first_name": request.user.first_name if request.user.is_authenticated else "Guest",
        "user_last_name": request.user.last_name if request.user.is_authenticated else "User",
        "user_email": request.user.email if request.user.is_authenticated else "",
        "my_plugins": 15,
        "smarter_version": __version__,
        "site_title": "My Awesome Site",
        "footer_message": "Copyright 2022. All rights reserved.",
    }
