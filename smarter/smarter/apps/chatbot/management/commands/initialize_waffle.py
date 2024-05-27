"""Initialize Waffle flags and switches."""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from waffle.models import Switch


# pylint: disable=E1101
class Command(BaseCommand):
    """Initialize Waffle flags and switches."""

    def handle(self, *args, **options):
        """ensure that switches exist. If not, then create them"""

        def verify_switch(switch_name):
            """Initialize a switch."""
            if not Switch.objects.filter(name=switch_name).exists():
                call_command("waffle_switch", switch_name, "off", "--create")
            else:
                print(f"Verified switch {switch_name}")

        switches = [
            "csrf_middleware_suppress_for_chatbots",
            "csrf_middleware_logging",
            "chatbothelper_logging",
            "chatbot_api_view_logging",
            "chat_logging",
            "chatapp_view_logging",
            "reactapp_debug_mode",
            "manifest_logging",
            "journal",
        ]

        for switch in switches:
            verify_switch(switch)
