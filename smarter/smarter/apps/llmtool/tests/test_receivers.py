# pylint: disable=wrong-import-position
"""
Test :mod:`smarter.apps.llmtool.receivers`, the package and each of its modules.

Most receivers only log. Their logger is replaced with a mock, so that these
tests can verify what each receiver logs regardless of the waffle switches
that enable receiver logging.
"""

from types import SimpleNamespace
from unittest import mock

from smarter.apps.llmtool import receivers, signals
from smarter.apps.llmtool.models import PluginMeta, PluginSelectorHistory
from smarter.apps.llmtool.signals import (
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
from smarter.lib import json, logging

from .base_classes import PluginAppTestBase, get_test_data

logger = logging.getLogger(__name__)

TASK_PATCH = "smarter.apps.llmtool.receivers.plugin.create_plugin_selector_history"
RECEIVER_MODULES = (
    receivers.api,
    receivers.extension,
    receivers.image_search,
    receivers.models,
    receivers.plugin,
    receivers.skill,
    receivers.sql,
    receivers.websearch,
)


# pylint: disable=too-many-public-methods
class TestPluginReceivers(PluginAppTestBase):
    """Test the plugin app's signal and model receivers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.selector_history = get_test_data("selector-history.yaml")

    def setUp(self):
        super().setUp()
        # every receivers module has its own logger. They share one mock.
        self.logger = mock.MagicMock()
        for module in RECEIVER_MODULES:
            patcher = mock.patch.object(module, "logger", self.logger)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.messages: list[str] = []
        # messages are formatted when they are logged, while the models they
        # describe still exist.
        self.logger.debug.side_effect = self.log
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
        # the message names the sender, whatever its kind, not the llmtool receivers module.
        self.assertIn(f"{self.__class__.__name__}.broker_ready()", self.logged())

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

    # -------------------------------------------------------------------------
    # request lifecycle signals
    # -------------------------------------------------------------------------
    def test_request_lifecycle(self):
        """Test that each request lifecycle receiver logs its signal, and logs failures as warnings."""
        plugin = self.static_plugin
        for family in ("sql", "api", "image_search", "skill"):
            cases = {
                "request_started": {"function_args": {"q": "gobstoppers"}},
                "responded": {"response": [{"name": "Willy"}], "cached": True, "sql": "SELECT 1;", "query": "q"},
                "failed": {"error": "it broke"},
                "request_completed": {"success": False, "duration": 0.25},
            }
            if family != "skill":
                cases["authenticated"] = {"connection": "db", "auth_method": "token", "status_code": 200}
                cases["authentication_failed"] = {"error": "HTTP 401", "status_code": 401, "provider": "brave"}
            for event, kwargs in cases.items():
                name = f"{family}_plugin_{event}"
                with self.subTest(signal=name):
                    self.messages.clear()
                    self.logger.reset_mock()
                    getattr(signals, name).send(sender=self.__class__, plugin=plugin, **kwargs)
                    self.assertIn(name, self.logged())
                    self.assertIn(plugin.name, self.logged())
                    if event in ("failed", "authentication_failed"):
                        self.logger.warning.assert_called_once()
                        self.assertIn(kwargs["error"], self.logged())
                    else:
                        self.logger.info.assert_called_once()
        self.messages.clear()
        signals.api_plugin_responded.send(sender=self.__class__, plugin=plugin, response="abc", cached=False)
        self.assertIn("characters: 3", self.logged())
        signals.sql_plugin_request_completed.send(sender=self.__class__, plugin=plugin, success=True, duration=1.5)
        self.assertIn("duration: 1.500s", self.logged())

    def test_response_characters(self):
        """Test the length of a response, as the responded receivers log it."""
        self.assertEqual(receivers.response_characters(None), 0)
        self.assertEqual(receivers.response_characters("abcd"), 4)
        self.assertEqual(receivers.response_characters([1, 2]), len(json.dumps([1, 2])))

    def test_skill_retrieval(self):
        """Test the SkillPlugin retrieval receivers."""
        url = "https://github.com/anthropics/skills/tree/main/skills/pdf"
        signals.skill_plugin_retrieval_started.send(sender=self.__class__, plugin=self.static_plugin, url=url)
        signals.skill_plugin_retrieved.send(
            sender=self.__class__, plugin=self.static_plugin, url=url, skill_name="pdf", resource_count=4, duration=1.0
        )
        self.assertIn("skill_name: pdf resource_count: 4", self.logged())
        signals.skill_plugin_retrieval_failed.send(
            sender=self.__class__, plugin=self.static_plugin, url=url, error="SKILL.md was not found", duration=0.1
        )
        self.logger.warning.assert_called_once()
        self.assertIn("SKILL.md was not found", self.logged())

    # -------------------------------------------------------------------------
    # extension signals
    # -------------------------------------------------------------------------
    def test_extensions(self):
        """Test the extension receivers."""
        extension = SimpleNamespace(slug="weather")
        version = SimpleNamespace(version="1.1.0")
        tool = {"slug": "weather", "version": "1.1.0", "tool_name": "get_weather"}
        signals.extension_installed.send(sender=self.__class__, extension=extension, version=version)
        self.assertIn("extension_installed", self.logged())
        signals.extension_upgraded.send(
            sender=self.__class__, extension=extension, version=version, previous_version="1.0.0"
        )
        self.assertIn("previous_version: 1.0.0", self.logged())
        signals.extension_enabled.send(sender=self.__class__, extension=extension)
        signals.extension_uninstalled.send(sender=self.__class__, slug="weather")
        signals.extension_tool_called.send(sender=self.__class__, arguments={"city": "Paris"}, **tool)
        self.assertIn("Paris", self.logged())
        signals.extension_tool_responded.send(sender=self.__class__, characters=1024, **tool)
        self.assertIn("characters: 1024", self.logged())
        signals.extension_tool_completed.send(sender=self.__class__, success=True, duration=0.5, **tool)
        self.assertIn("success: True duration: 0.500s", self.logged())
        self.logger.warning.assert_not_called()
        signals.extension_disabled.send(sender=self.__class__, extension=extension, reason="disabled by admin")
        signals.extension_tool_failed.send(sender=self.__class__, error="timed out", **tool)
        self.assertEqual(self.logger.warning.call_count, 2)
        self.assertIn("disabled by admin", self.logged())
        self.assertIn("timed out", self.logged())
