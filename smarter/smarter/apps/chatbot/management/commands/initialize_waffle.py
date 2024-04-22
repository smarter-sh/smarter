"""Initialize Waffle flags and switches."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


# pylint: disable=E1101
class Command(BaseCommand):
    """Initialize Waffle flags and switches."""

    def handle(self, *args, **options):
        """Handle the command."""
        call_command("waffle_switch", "chatbot_suppress_csrf", "off", "--create")
        call_command("waffle_switch", "chatbot_log_csrf", "off", "--create")
        call_command("waffle_switch", "chatbothelper_logging", "on", "--create")
