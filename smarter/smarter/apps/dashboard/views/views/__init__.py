"""This module contains the view classes for the dashboard application."""

from .change_log import ChangeLogView
from .coming_soon import ComingSoon
from .dashboard import DashboardView
from .dropzone import DropzoneView
from .email_added import EmailAdded
from .notifications import NotificationsView

__all__ = [
    "ChangeLogView",
    "ComingSoon",
    "EmailAdded",
    "DashboardView",
    "DropzoneView",
    "NotificationsView",
]
