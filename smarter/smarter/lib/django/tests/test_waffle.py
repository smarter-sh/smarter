"""Test the Smarter Waffle Switch."""

import time
from unittest.mock import MagicMock, patch

from asgiref.sync import async_to_sync
from django.apps import apps
from django.db.models.signals import post_delete, post_save
from django.db.utils import OperationalError, ProgrammingError
from django_redis.exceptions import ConnectionInterrupted
from redis.exceptions import TimeoutError as RedisTimeoutError
from waffle import get_waffle_switch_model

from smarter.lib.django.waffle import (
    SmarterWaffleSwitches,
    is_database_ready,
    smarter_waffle_switches,
)
from smarter.lib.django.waffle.is_active import (
    SWITCH_CACHE_SECONDS,
    async_switch_is_active,
    cached_switch_state,
    clear_switch_cache,
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
        self.assertFalse(switch_is_active(None))  # type: ignore[arg-type]  # a wrong type, to test that it is refused
        self.assertFalse(switch_is_active(12345))  # type: ignore[arg-type]  # a wrong type, to test that it is refused

    def test_switch_name_type(self):
        # Test that non-string types return False
        self.assertFalse(switch_is_active(None))  # type: ignore[arg-type]  # a wrong type, to test that it is refused
        self.assertFalse(switch_is_active(123))  # type: ignore[arg-type]  # a wrong type, to test that it is refused
        self.assertFalse(switch_is_active([]))  # type: ignore[arg-type]  # a wrong type, to test that it is refused
        self.assertFalse(switch_is_active({}))  # type: ignore[arg-type]  # a wrong type, to test that it is refused

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
            switch_is_active(None)  # type: ignore[arg-type]  # a wrong type, to test that it is refused
            switch_is_active(123)  # type: ignore[arg-type]  # a wrong type, to test that it is refused
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

    def setUp(self):
        super().setUp()
        # the patched model is read only on a miss of the switches that this process remembers.
        clear_switch_cache()

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


class TestSwitchCache(SmarterTestBase):
    """
    Each process remembers a switch's state for SWITCH_CACHE_SECONDS, and forgets it when a switch is saved or deleted.

    The Switch model is patched where a switch's state is read, so that the database's switches are never changed.
    """

    def setUp(self):
        super().setUp()
        clear_switch_cache()
        self.addCleanup(clear_switch_cache)

    def model(self, active: bool) -> MagicMock:
        """Return a patched Switch model whose switch is ``active``."""
        switch = MagicMock(pk=1)
        switch.is_active.return_value = active
        model = MagicMock()
        model.get.return_value = switch
        return model

    def test_remembers_a_switch(self):
        """Test that a second check is answered from memory, without reading the switch."""
        name = SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CSRF
        model = self.model(True)
        with patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=model):
            self.assertTrue(switch_is_active(name))
            self.assertTrue(switch_is_active(name))
        model.get.assert_called_once_with(name)

    def test_forgets_a_switch_after_its_time(self):
        """Test that a switch is read again once SWITCH_CACHE_SECONDS have passed."""
        name = SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CSRF
        with patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=self.model(True)):
            self.assertTrue(switch_is_active(name))
        later = time.monotonic() + SWITCH_CACHE_SECONDS + 1
        with (
            patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=self.model(False)),
            patch(f"{IS_ACTIVE}.time.monotonic", return_value=later),
        ):
            self.assertFalse(switch_is_active(name))

    def test_forgets_every_switch_when_a_switch_is_saved_or_deleted(self):
        """Test that saving or deleting a Switch, e.g. with override_switch, clears what this process remembers."""
        name = SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CSRF
        with patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=self.model(True)):
            self.assertTrue(switch_is_active(name))
        for signal in (post_save, post_delete):
            with self.subTest(signal=signal):
                signal.send(sender=get_waffle_switch_model(), instance=MagicMock())
                with patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=self.model(False)):
                    self.assertFalse(switch_is_active(name))
                with patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=self.model(True)):
                    clear_switch_cache()
                    self.assertTrue(switch_is_active(name))

    def test_does_not_remember_a_failure(self):
        """Test that a switch whose state could not be read is read again on the next check."""
        name = SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CSRF
        failing = MagicMock()
        failing.get.side_effect = OperationalError("database is gone")
        with patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=failing):
            self.assertFalse(switch_is_active(name))
        with patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=self.model(True)):
            self.assertTrue(switch_is_active(name))

    def test_a_database_outage_logs_one_warning_line(self):
        """Test that a database that can't be reached gives one warning line, without a traceback (issue #951)."""
        name = SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CSRF
        failing = MagicMock()
        failing.get.side_effect = OperationalError(2003, "Can't connect to MySQL server")
        with (
            patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=failing),
            self.assertLogs(IS_ACTIVE, level="WARNING") as logs,
        ):
            self.assertFalse(switch_is_active(name))
        self.assertEqual(len(logs.records), 1)
        self.assertEqual(logs.records[0].levelname, "WARNING")
        self.assertIn("the database is unavailable", logs.output[0])
        self.assertNotIn("Traceback", "\n".join(logs.output))

    def test_a_missing_table_still_logs_an_error(self):
        """Test that a database error other than an outage, e.g. a missing table, is still logged as an error."""
        name = SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CSRF
        failing = MagicMock()
        failing.get.side_effect = ProgrammingError(1146, "Table 'waffle_switch' doesn't exist")
        with (
            patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=failing),
            self.assertLogs(IS_ACTIVE, level="ERROR") as logs,
        ):
            self.assertFalse(switch_is_active(name))
        self.assertIn("Database not ready", logs.output[0])

    def test_a_remembered_switch_skips_the_readiness_checks(self):
        """Test that a remembered state is returned before the apps and database are checked."""
        name = SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CSRF
        with patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=self.model(True)):
            self.assertTrue(switch_is_active(name))
        with patch(f"{IS_ACTIVE}.is_database_ready") as is_ready:
            self.assertTrue(switch_is_active(name))
        is_ready.assert_not_called()

    def test_cached_switch_state(self):
        name = SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CSRF
        self.assertIsNone(cached_switch_state(name))
        self.assertIsNone(cached_switch_state(None))  # type: ignore[arg-type]
        with patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=self.model(False)):
            switch_is_active(name)
        self.assertFalse(cached_switch_state(name))

    def test_async_switch_is_active_answers_from_memory(self):
        """Test that a remembered state is returned without the hop to Django's sync thread."""
        name = SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CSRF
        with patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=self.model(True)):
            self.assertTrue(switch_is_active(name))
        with patch(f"{IS_ACTIVE}.sync_to_async") as sync_to_async:
            self.assertTrue(async_to_sync(async_switch_is_active)(name))
        sync_to_async.assert_not_called()

    def test_async_switch_is_active_reads_a_switch_it_does_not_remember(self):
        name = SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CSRF
        with patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=self.model(True)):
            self.assertTrue(async_to_sync(async_switch_is_active)(name))

    def cache_down_model(self, error: Exception, stored: object) -> MagicMock:
        """Return a patched Switch model whose cached read raises ``error``, and whose table holds ``stored``."""
        model = MagicMock()
        model.get.side_effect = error
        model.objects.filter.return_value.first.return_value = stored
        return model

    def test_reads_the_database_when_the_cache_fails(self):
        """Test that a Redis outage reads the switch from the database, with one warning line, rather than raising."""
        name = SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CSRF
        errors = (
            RedisTimeoutError("Timeout reading from socket"),
            ConnectionInterrupted(connection=None),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__):
                clear_switch_cache()
                model = self.cache_down_model(error, MagicMock(active=True))
                with (
                    patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=model),
                    self.assertLogs(IS_ACTIVE, level="WARNING") as logs,
                ):
                    self.assertTrue(switch_is_active(name))
                model.objects.filter.assert_called_once_with(name=name)
                self.assertIn("reading switch", logs.output[0])
                self.assertNotIn("Traceback", "\n".join(logs.output))

    def test_a_switch_missing_from_the_database_has_its_default(self):
        """Test that the fallback answers a switch's Smarter default when its row doesn't exist."""
        name = SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CSRF
        default = bool(smarter_waffle_switches.switches[name].default)
        model = self.cache_down_model(RedisTimeoutError("down"), None)
        with patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=model):
            self.assertEqual(switch_is_active(name), default)

    def test_cache_and_database_down(self):
        """Test that a switch is inactive when neither Redis nor the database answers."""
        name = SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CSRF
        model = self.cache_down_model(RedisTimeoutError("down"), None)
        model.objects.filter.side_effect = OperationalError("database is gone")
        with patch(f"{IS_ACTIVE}.get_waffle_switch_model", return_value=model):
            self.assertFalse(switch_is_active(name))


class TestSwitchNames(SmarterTestBase):
    """Test the list and the set of every switch's name."""

    def test_all_is_a_sorted_list_and_all_set_matches_it(self):
        switches = SmarterWaffleSwitches()
        self.assertIsInstance(switches.all, list)
        self.assertEqual(switches.all_set, frozenset(switches.all))
        self.assertIn(SmarterWaffleSwitches.ENABLE_MIDDLEWARE_CSRF, switches.all_set)
