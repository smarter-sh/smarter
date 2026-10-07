# pylint: disable=wrong-import-position
"""
Test :mod:`smarter.apps.plugin.receivers`.

Most receivers only log. Their logger is replaced with a mock, so that these
tests can verify what each receiver logs regardless of the waffle switches
that enable receiver logging.
"""

from unittest import mock

from smarter.apps.plugin import receivers
from smarter.apps.plugin.models import PluginMeta, PluginSelectorHistory
from smarter.apps.plugin.signals import (
    broker_ready,
    plugin_called,
    plugin_cloned,
    plugin_created,
    plugin_deleted,
    plugin_deleting,
    plugin_ready,
    plugin_responded,
    plugin_selected,
    plugin_updated,
    websearch_failed,
    websearch_fetched,
    websearch_searched,
)
from smarter.lib import logging

from .base_classes import PluginAppTestBase, get_test_data

logger = logging.getLogger(__name__)

TASK_PATCH = "smarter.apps.plugin.receivers.create_plugin_selector_history"


# pylint: disable=too-many-public-methods
class TestPluginReceivers(PluginAppTestBase):
    """Test the plugin app's signal and model receivers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.selector_history = get_test_data("selector-history.yaml")

    def setUp(self):
        super().setUp()
        patcher = mock.patch.object(receivers, "logger")
        self.logger = patcher.start()
        self.addCleanup(patcher.stop)
        self.messages: list[str] = []
        # messages are formatted when they are logged, while the models they
        # describe still exist.
        self.logger.info.side_effect = self.log
        self.logger.warning.side_effect = self.log

    def log(self, msg, *args, **kwargs):  # pylint: disable=W0613
        """Record a formatted log message."""
        self.messages.append(msg % args if args else msg)

    def logged(self) -> str:
        """Return everything the receivers logged, as one string."""
        return "\n".join(self.messages)

    # -------------------------------------------------------------------------
    # plugin lifecycle signals
    # -------------------------------------------------------------------------
    def test_plugin_created(self):
        """Test the plugin_created receiver."""
        plugin_created.send(sender=self.__class__, plugin=self.static_plugin)
        self.assertIn("plugin_created", self.logged())
        self.assertIn(self.static_plugin.name, self.logged())

    def test_plugin_cloned(self):
        """Test the plugin_cloned receiver."""
        plugin_cloned.send(sender=self.__class__, plugin=self.static_plugin)
        self.assertIn("plugin_cloned", self.logged())

    def test_plugin_updated(self):
        """Test the plugin_updated receiver."""
        plugin_updated.send(sender=self.__class__, plugin=self.static_plugin)
        self.assertIn("plugin_updated", self.logged())

    def test_plugin_deleting(self):
        """Test the plugin_deleting receiver."""
        plugin_deleting.send(
            sender=self.__class__, plugin=self.static_plugin, plugin_meta=self.static_plugin.plugin_meta
        )
        self.assertIn("plugin_deleting", self.logged())
        self.assertIn(self.static_plugin.name, self.logged())

    def test_plugin_deleted(self):
        """Test the plugin_deleted receiver."""
        plugin_deleted.send(
            sender=self.__class__,
            plugin=self.static_plugin,
            plugin_meta=self.static_plugin.plugin_meta,
            plugin_name="a_deleted_plugin",
        )
        self.assertIn("a_deleted_plugin", self.logged())

    def test_plugin_called(self):
        """Test the plugin_called receiver."""
        plugin_called.send(sender=self.__class__, plugin=self.static_plugin, inquiry_type="couponCodes")
        self.assertIn("couponCodes", self.logged())

    def test_plugin_responded(self):
        """Test that the plugin_responded receiver logs the plugin's response."""
        plugin_responded.send(
            sender=self.__class__, plugin=self.static_plugin, inquiry_type="contact", response={"name": "Willy"}
        )
        self.assertIn("Willy", self.logged())

    def test_plugin_responded_json_string(self):
        """Test that the plugin_responded receiver decodes a JSON string response."""
        plugin_responded.send(
            sender=self.__class__, plugin=self.static_plugin, inquiry_type="contact", response='{"name": "Wonka"}'
        )
        self.assertIn("Wonka", self.logged())

    def test_plugin_responded_plain_string(self):
        """Test that the plugin_responded receiver logs a response that is not JSON as is."""
        plugin_responded.send(
            sender=self.__class__, plugin=self.static_plugin, inquiry_type="contact", response="not json"
        )
        self.assertIn("not json", self.logged())

    def test_plugin_ready(self):
        """Test the plugin_ready receiver."""
        plugin_ready.send(sender=self.__class__, plugin=self.static_plugin)
        self.assertIn("plugin_ready", self.logged())

    def test_broker_ready(self):
        """Test the broker_ready receiver."""
        broker = mock.MagicMock()
        broker.kind = "Plugin"
        broker.name = "a_broker"
        broker_ready.send(sender=self.__class__, broker=broker)
        self.assertIn("a_broker", self.logged())

    # -------------------------------------------------------------------------
    # plugin_selected
    # -------------------------------------------------------------------------
    def test_plugin_selected_input_text(self):
        """Test that the plugin_selected receiver queues the selector history task, for input text."""
        kwargs = self.selector_history["input_text"]
        with mock.patch(TASK_PATCH) as task:
            plugin_selected.send(
                sender=self.__class__,
                plugin=self.static_plugin,
                user=self.admin_user,
                input_text=kwargs["input_text"],
                search_term=kwargs["search_term"],
            )
        task.delay.assert_called_once_with(
            plugin_id=self.static_plugin.id,
            user_id=self.admin_user.id,
            input_text=kwargs["input_text"],
            messages=[],
            search_term=kwargs["search_term"],
        )

    def test_plugin_selected_messages(self):
        """Test that the plugin_selected receiver queues the selector history task, for messages."""
        kwargs = self.selector_history["messages"]
        with mock.patch(TASK_PATCH) as task:
            plugin_selected.send(
                sender=self.__class__,
                plugin=self.static_plugin,
                user=self.admin_user,
                messages=kwargs["messages"],
                search_term=kwargs["search_term"],
            )
        task.delay.assert_called_once_with(
            plugin_id=self.static_plugin.id,
            user_id=self.admin_user.id,
            input_text=None,
            messages=kwargs["messages"],
            search_term=kwargs["search_term"],
        )

    def test_plugin_selected_without_plugin(self):
        """Test that the plugin_selected receiver does not queue the task without a plugin."""
        with mock.patch(TASK_PATCH) as task:
            plugin_selected.send(sender=self.__class__, plugin=None, user=self.admin_user, input_text="hello")
        task.delay.assert_not_called()
        self.logger.warning.assert_called()

    def test_plugin_selected_by_selector(self):
        """Test that a plugin's selector sends plugin_selected when the input text refers to a search term."""
        name = "test_plugin_app_receivers_selected"
        plugin = self.new_static_plugin(name)
        with mock.patch(TASK_PATCH) as task:
            self.assertTrue(plugin.selected(user=self.admin_user, input_text="I love a Wonka Bar"))
        task.delay.assert_called_once()
        self.assertEqual(task.delay.call_args.kwargs["plugin_id"], plugin.id)
        self.assertEqual(task.delay.call_args.kwargs["search_term"], "Wonka Bar")

    # -------------------------------------------------------------------------
    # websearch signals
    # -------------------------------------------------------------------------
    def test_websearch_searched(self):
        """Test the websearch_searched receiver."""
        websearch_searched.send(
            sender=self.__class__,
            plugin=self.static_plugin,
            query="gobstoppers",
            provider="brave",
            result_count=5,
            cached=False,
        )
        self.assertIn("gobstoppers", self.logged())
        self.assertIn("brave", self.logged())

    def test_websearch_fetched(self):
        """Test the websearch_fetched receiver."""
        websearch_fetched.send(
            sender=self.__class__,
            plugin=self.static_plugin,
            url="https://example.com/a",
            final_url="https://example.com/b",
            characters=1234,
            truncated=False,
            cached=True,
        )
        self.assertIn("https://example.com/b", self.logged())

    def test_websearch_failed(self):
        """Test that the websearch_failed receiver logs a warning."""
        websearch_failed.send(
            sender=self.__class__,
            plugin=self.static_plugin,
            operation="fetch",
            target="https://example.com/a",
            error="HTTP 404",
        )
        self.logger.warning.assert_called_once()
        self.assertIn("HTTP 404", self.logged())

    # -------------------------------------------------------------------------
    # model receivers
    # -------------------------------------------------------------------------
    def test_model_created(self):
        """Test that the post_save receivers log each model that a new plugin creates."""
        self.new_static_plugin("test_plugin_app_receivers_created")
        logged = self.logged()
        self.assertIn("PluginMeta() record created", logged)
        self.assertIn("PluginSelector() record created", logged)
        self.assertIn("PluginPrompt() record created", logged)
        self.assertIn("PluginDataStatic() record created", logged)

    def test_model_updated(self):
        """Test that the post_save receivers log an updated model."""
        plugin = self.new_static_plugin("test_plugin_app_receivers_updated")
        self.messages.clear()
        plugin_meta: PluginMeta = plugin.plugin_meta  # type: ignore[assignment]
        plugin_meta.description = "An updated description."
        plugin_meta.save()
        self.assertIn("PluginMeta() record updated", self.logged())

    def test_model_deleted(self):
        """Test that the pre_delete receivers log each model that a deleted plugin deletes."""
        name = "test_plugin_app_receivers_deleted"
        self.new_static_plugin(name)
        self.messages.clear()
        self.delete_plugin_by_name(name)
        logged = self.logged()
        self.assertIn("PluginMeta().pre_delete()", logged)
        self.assertIn("PluginSelector().pre_delete()", logged)
        self.assertIn("PluginPrompt().pre_delete()", logged)
        self.assertIn("PluginDataStatic().pre_delete()", logged)

    def test_selector_history(self):
        """Test that the post_save and pre_delete receivers log PluginSelectorHistory."""
        history = PluginSelectorHistory.objects.create(
            plugin_selector=self.static_plugin.plugin_selector, search_term="Gobstopper", messages=[]
        )
        self.assertIn("PluginSelectorHistory() created", self.logged())
        history.delete()
        self.assertIn("PluginSelectorHistory().pre_delete()", self.logged())
