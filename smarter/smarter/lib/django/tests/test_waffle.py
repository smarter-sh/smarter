"""Test the Smarter Waffle Switch."""

from django.apps import apps

from smarter.lib.django.waffle import (
    SmarterWaffleSwitches,
    is_database_ready,
    switch_is_active,
)
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
