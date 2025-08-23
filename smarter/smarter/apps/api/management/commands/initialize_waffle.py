"""Initialize Waffle flags and switches."""

from django.core.management import call_command
from django.core.management.base import BaseCommand
from waffle.models import Switch

from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.lib.django.waffle import SmarterWaffleSwitches


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

        smarter_switches = SmarterWaffleSwitches().all.copy()

        for switch in smarter_switches:
            verify_switch(switch)

        waffle_switches = Switch.objects.all()
        for switch in waffle_switches:
            if not switch.name in smarter_switches:
                self.stdout.write(self.style.NOTICE(f"Deleting orphaned switch {switch.name}."))
                switch.delete()

        if smarter_settings.environment == SmarterEnvironments.LOCAL:
            call_command("waffle_switch", SmarterWaffleSwitches.REACTAPP_DEBUG_MODE, "on")
