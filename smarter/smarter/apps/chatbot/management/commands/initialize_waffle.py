"""Initialize Waffle flags and switches."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


# pylint: disable=E1101
class Command(BaseCommand):
    """Initialize Waffle flags and switches."""

    def handle(self, *args, **options):
        """Handle the command."""
        call_command("waffle_switch", "csrf_middleware_suppress_for_chatbots", "off", "--create")
        call_command("waffle_switch", "csrf_middleware_logging", "off", "--create")
        call_command("waffle_switch", "chatbothelper_logging", "off", "--create")
        call_command("waffle_switch", "chatbot_api_view_logging", "off", "--create")
        call_command("waffle_switch", "chat_logging", "off", "--create")
