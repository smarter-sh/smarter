# pylint: disable=wrong-import-position
"""
Test :mod:`smarter.apps.plugin.tasks`.

The Celery tasks are called directly, which runs them synchronously, in this
process. An exception that a task raises is re-raised rather than retried.
"""

from smarter.apps.plugin.models import PluginSelectorHistory
from smarter.apps.plugin.plugin.base import SmarterPluginError
from smarter.apps.plugin.tasks import (
    create_plugin_charge,
    create_plugin_selector_history,
)
from smarter.common.const import SMARTER_CHAT_SESSION_KEY_NAME
from smarter.lib import logging

from .base_classes import PluginAppTestBase, get_test_data

logger = logging.getLogger(__name__)


class TestPluginTasks(PluginAppTestBase):
    """Test create_plugin_selector_history() and create_plugin_charge()."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.selector_history = get_test_data("selector-history.yaml")

    def setUp(self):
        super().setUp()
        self.addCleanup(self.delete_history)

    def history(self):
        """Return the static plugin's PluginSelectorHistory."""
        return PluginSelectorHistory.objects.filter(plugin_selector=self.static_plugin.plugin_selector)

    def delete_history(self):
        """Delete the static plugin's PluginSelectorHistory."""
        self.history().delete()

    def test_input_text(self):
        """Test that the history records the input text, search term and session key."""
        kwargs = dict(self.selector_history["input_text"])
        session_key = kwargs.pop("session_key")
        kwargs[SMARTER_CHAT_SESSION_KEY_NAME] = session_key
        create_plugin_selector_history(user_id=self.admin_user.id, plugin_id=self.static_plugin.id, **kwargs)  # type: ignore

        history = self.history()
        self.assertEqual(history.count(), 1)
        record = history.first()
        self.assertEqual(record.search_term, kwargs["search_term"])  # type: ignore[union-attr]
        self.assertEqual(record.messages, {"input_text": kwargs["input_text"]})  # type: ignore[union-attr]
        self.assertEqual(record.session_key, session_key)  # type: ignore[union-attr]

    def test_messages(self):
        """Test that the history records the messages, when there is no input text."""
        kwargs = self.selector_history["messages"]
        create_plugin_selector_history(user_id=self.admin_user.id, plugin_id=self.static_plugin.id, **kwargs)  # type: ignore

        record = self.history().first()
        self.assertIsNotNone(record)
        self.assertEqual(record.search_term, kwargs["search_term"])  # type: ignore[union-attr]
        self.assertEqual(record.messages, kwargs["messages"])  # type: ignore[union-attr]

    def test_user_profile_id(self):
        """Test that the task resolves the user profile from user_profile_id."""
        kwargs = self.selector_history["input_text"]
        create_plugin_selector_history(
            user_profile_id=self.user_profile.id, plugin_id=self.static_plugin.id, **kwargs  # type: ignore
        )
        self.assertEqual(self.history().count(), 1)

    def test_non_admin_user(self):
        """Test that the history is recorded for a user with whom the plugin is shared."""
        kwargs = self.selector_history["input_text"]
        create_plugin_selector_history(user_id=self.non_admin_user.id, plugin_id=self.static_plugin.id, **kwargs)  # type: ignore
        self.assertEqual(self.history().count(), 1)

    def test_unresolved_user(self):
        """Test that the task raises if it cannot resolve the user profile."""
        with self.assertRaises(SmarterPluginError):
            create_plugin_selector_history(plugin_id=self.static_plugin.id, **self.selector_history["input_text"])
        self.assertEqual(self.history().count(), 0)

    def test_unknown_plugin(self):
        """Test that the task records nothing for a plugin that does not exist."""
        create_plugin_selector_history(
            user_id=self.admin_user.id, plugin_id=999999999, **self.selector_history["input_text"]  # type: ignore
        )
        self.assertEqual(self.history().count(), 0)

    def test_missing_plugin_id(self):
        """Test that the task records nothing when there is no plugin id."""
        create_plugin_selector_history(user_id=self.admin_user.id, **self.selector_history["input_text"])  # type: ignore
        self.assertEqual(self.history().count(), 0)

    def test_create_plugin_charge(self):
        """Test that create_plugin_charge() is not yet implemented, and does nothing."""
        self.assertIsNone(create_plugin_charge(plugin_id=self.static_plugin.id))
