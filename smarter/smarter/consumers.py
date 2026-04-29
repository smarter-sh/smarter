"""
WebSocket URL routing for the smarter application, including prompt-related
consumers.
"""

from smarter.apps.dashboard.views.logs import consumers as dashboard_logs_consumers

urlpatterns = [
    *dashboard_logs_consumers.urlpatterns,
]

__all__ = ["urlpatterns"]
