"""Test the Smarter Waffle Switch."""

from unittest.mock import MagicMock, patch

from django.apps import apps

from smarter.lib.django.waffle import (
    SmarterWaffleSwitches,
    is_database_ready,
    smarter_waffle_switches,
)
from smarter.lib.django.waffle.is_active import switch_is_active
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestSwitchIsActive(SmarterTestBase):
    """
    Unit tests for switch_is_active function.

    These tests do not use Mock or patch, and will run against the actual database and waffle configuration.
    """

    def test_valid_switch_returns_bool(self):
        # Test that a valid switch returns a boolean (True or False)
        switches = SmarterWaffleSwitches().all
        for switch in switches:
            result = switch_is_active(switch)
            self.assertIsInstance(result, bool, f"Switch '{switch}' did not return a bool")

    def test_invalid_switch_returns_false(self):
        # Test that an invalid switch name returns False
        self.assertFalse(switch_is_active("not_a_real_switch"))
        self.assertFalse(switch_is_active(""))
        self.assertFalse(switch_is_active(None))
        self.assertFalse(switch_is_active(12345))

    def test_switch_name_type(self):
        # Test that non-string types return False
        self.assertFalse(switch_is_active(None))
        self.assertFalse(switch_is_active(123))
        self.assertFalse(switch_is_active([]))
        self.assertFalse(switch_is_active({}))

    def test_switch_is_active_db_ready(self):
        # If the DB is ready, valid switches should return bool
        if is_database_ready():
            for switch in SmarterWaffleSwitches().all:
                result = switch_is_active(switch)
                self.assertIsInstance(result, bool)
        else:
            self.skipTest("Database is not ready")

    def test_switch_is_active_app_registry(self):
        # If the app registry is not ready, should return False
        # This is hard to simulate without patching, so just check that when ready, valid switches work
        if apps.ready:
            for switch in SmarterWaffleSwitches().all:
                self.assertIsInstance(switch_is_active(switch), bool)
        else:
            self.skipTest("App registry is not ready")

    def test_all_switches_are_valid(self):
        # All switches in SmarterWaffleSwitches should be valid
        for switch in SmarterWaffleSwitches().all:
            self.assertIn(switch, SmarterWaffleSwitches().all)

    def test_switch_is_active_error_handling(self):
        # Should not raise exceptions for any input
        try:
            switch_is_active("not_a_real_switch")
            switch_is_active(None)
            switch_is_active(123)
            switch_is_active("")
        # pylint: disable=broad-except
        except Exception as e:
            self.fail(f"switch_is_active raised an exception: {e}")


IS_ACTIVE = "smarter.lib.django.waffle.is_active"


class TestMissingSwitch(SmarterTestBase):
    """
    A switch that is checked before it exists is created with its Smarter default, rather than with.

    django-waffle's global default, which is inactive. The Switch model is patched, so that the
    database's switches are never changed.
    """

    def check_missing(self, switch_name: str) -> MagicMock:
        """Check a missing switch, and return the patched Switch model."""
        default = smarter_waffle_switches.switches[switch_name].default
        created = MagicMock(active=default)
        created.is_active.return_value = default
        model = MagicMock()
        model.get.return_value = MagicMock(pk=None)
        model.objects.get_or_create.return_value = (created, True)
        with patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=model), patch(f"{IS_ACTIVE}.get_cache"):
            self.assertIs(switch_is_active(switch_name), default)
        return model

    def test_creates_an_active_by_default_switch_as_active(self):
        name = SmarterWaffleSwitches.ENABLE_WEB_CONSOLE_SERVER_LOGS
        model = self.check_missing(name)
        model.objects.get_or_create.assert_called_once_with(
            name=name,
            defaults={"active": True, "note": smarter_waffle_switches.switches[name].comment},
        )

    def test_creates_an_inactive_by_default_switch_as_inactive(self):
        name = SmarterWaffleSwitches.ENABLE_DEBUG_MODE
        model = self.check_missing(name)
        self.assertFalse(model.objects.get_or_create.call_args.kwargs["defaults"]["active"])

    def test_does_not_create_an_existing_switch(self):
        existing = MagicMock(pk=1)
        existing.is_active.return_value = False
        model = MagicMock()
        model.get.return_value = existing
        with patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=model):
            self.assertFalse(switch_is_active(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CSRF))
        model.objects.get_or_create.assert_not_called()
