"""This module contains the view classes for the dashboard application."""

from .coming_soon import ComingSoon
from .dashboard import DashboardView
from .email_added import EmailAdded

__all__ = [
    "ComingSoon",
    "EmailAdded",
    "DashboardView",
]
