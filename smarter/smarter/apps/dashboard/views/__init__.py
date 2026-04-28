"""
Views for the dashboard app.
"""

from .dashboard import ChangeLogView, DashboardView, EmailAdded, NotificationsView
from .logs import TerminalEmulatorLogView
from .manifest_drop_zone import ManifestDropZoneView
from .profile import ProfileLanguageView, ProfileView
from .prompt_passthrough_view import PromptPassthroughView

__all__ = [
    "ChangeLogView",
    "EmailAdded",
    "NotificationsView",
    "DashboardView",
    "TerminalEmulatorLogView",
    "ManifestDropZoneView",
    "ProfileView",
    "ProfileLanguageView",
    "PromptPassthroughView",
]
