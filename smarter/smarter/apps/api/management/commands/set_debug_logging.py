"""Initialize Waffle flags and switches."""

import logging

from django.core.management import call_command

from smarter.lib.django.management.base import SmarterCommand
from smarter.lib.django.waffle import SmarterWaffleSwitches


# pylint: disable=E1101
class Command(SmarterCommand):
    """
    Management command to enable or disable debug logging for the Smarter platform at runtime.

    This command allows administrators and developers to dynamically adjust the logging level of the application without requiring a restart. It also synchronizes the ENABLE_DEBUG_MODE Waffle switch to reflect the current debug state, ensuring consistency between feature flags and logging configuration.

    **Key Features and Workflow:**

    - Provides mutually exclusive --enable and --disable flags to toggle debug logging on or off.
    - Updates the ENABLE_DEBUG_MODE Waffle switch to match the selected logging state.
    - Sets the root logger's level to DEBUG when enabled, or INFO when disabled, affecting all log output immediately.
    - Can be used in any environment to quickly adjust logging verbosity for troubleshooting or monitoring.

    **Usage:**

    Run this command with either --enable or --disable to set the desired logging level:

        python manage.py set_logging --enable
        python manage.py set_logging --disable

    This is useful for debugging issues in production or development environments without redeploying or restarting services.

    **Error Handling and Output:**

    - Provides clear console output indicating the new logging state and Waffle switch status.
    - Handles invalid or missing arguments gracefully, requiring one of the two flags.

    **Intended Audience:**

    Developers, system administrators, and DevOps engineers responsible for monitoring and maintaining the Smarter platform. This command is especially useful for on-call engineers and support staff who need to adjust logging levels in real time.

    .. seealso::

        :py:class:`waffle.models.Switch` - The Django Waffle model representing feature switches.
        :py:class:`smarter.lib.django.waffle.SmarterWaffleSwitches` - The class defining all Smarter-specific Waffle switches.
        :py:data:`smarter.common.conf.settings.smarter_settings` - The Smarter settings module for environment detection.
    """

    def add_arguments(self, parser):
        """Add arguments to the command."""
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--enable", action="store_true", dest="enable", help="Enable debug mode")
        group.add_argument("--disable", action="store_true", dest="disable", help="Disable debug mode")

    def handle(self, *args, **options):
        """ensure that switches exist. If not, then create them"""

        def set_logging_level(level):
            """
            Set the logging level for the root logger and all its handlers.
            """

            logging.getLogger().setLevel(level)
            for handler in logging.getLogger().handlers:
                handler.setLevel(level)

            for _, logger in logging.Logger.manager.loggerDict.items():
                if isinstance(logger, logging.Logger):
                    logger.setLevel(level)
                    for handler in getattr(logger, "handlers", []):
                        handler.setLevel(level)

        self.handle_begin()

        if options["enable"]:
            call_command("waffle_switch", SmarterWaffleSwitches.ENABLE_DEBUG_MODE, "on")
            set_logging_level(logging.DEBUG)
        elif options["disable"]:
            call_command("waffle_switch", SmarterWaffleSwitches.ENABLE_DEBUG_MODE, "off")
            set_logging_level(logging.INFO)

        self.handle_completed_success()
