"""Initialize Waffle flags and switches."""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from waffle.models import Switch

from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SmarterEnvironments, SmarterWaffleSwitches


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

        switches = SmarterWaffleSwitches().all

        for switch in switches:
            verify_switch(switch)

        if smarter_settings.environment == SmarterEnvironments.LOCAL:
            call_command("waffle_switch", SmarterWaffleSwitches.REACTAPP_DEBUG_MODE, "on")
