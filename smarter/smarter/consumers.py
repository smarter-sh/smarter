"""
WebSocket URL routing for the smarter application, including prompt-related
consumers.
"""

from smarter.apps.prompt import consumers

urlpatterns = [
    *consumers.urlpatterns,
]

__all__ = ["urlpatterns"]
