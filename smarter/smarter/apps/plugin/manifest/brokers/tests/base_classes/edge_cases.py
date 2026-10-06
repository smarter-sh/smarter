"""Shared apply() and delete() edge-case tests for the plugin brokers."""

from http import HTTPStatus
from typing import Optional
from unittest.mock import MagicMock, PropertyMock, patch

from smarter.apps.plugin.manifest.brokers import SAMPluginBrokerError
from smarter.apps.plugin.manifest.brokers.plugin_base import SAMPluginBaseBroker
from smarter.apps.plugin.models import PluginMeta
from smarter.lib.manifest.broker import SAMBrokerError, SAMBrokerErrorNotReady


def fake_plugin_class(base: type, ready: bool = True, create_error=None, save_error=None) -> type:
    """
    Return a subclass of a plugin class whose instances skip all initialization.

    isinstance() checks against the real plugin class still pass, while create(),
    save() and ready are controlled by the test.
    """

    class FakePlugin(base):  # type: ignore[valid-type,misc]
        """A plugin that does nothing."""

        def __init__(self, *args, **kwargs):  # pylint: disable=super-init-not-called
            pass

        def __str__(self) -> str:
            return "FakePlugin"

        def __repr__(self) -> str:
            return "FakePlugin"

        def __bool__(self) -> bool:
            # PluginBase.__bool__ returns ready. A fake is always truthy, so that
            # a broker's ``if not self.plugin`` check doesn't hide its ready checks.
            return True

    FakePlugin.ready = ready  # type: ignore[attr-defined]
    FakePlugin.create = MagicMock(side_effect=create_error)  # type: ignore[attr-defined]
    FakePlugin.save = MagicMock(side_effect=save_error)  # type: ignore[attr-defined]
    FakePlugin.delete = MagicMock()  # type: ignore[attr-defined]
    return FakePlugin


class PluginBrokerEdgeCasesMixin:
    """
    Apply() and delete() error paths shared by every plugin broker.

    Mix into a TestSAMBrokerBaseClass subclass and set ``plugin_class`` to the
    broker's plugin class. ``apply_builds_plugin`` is True for the brokers whose
    apply() constructs a new plugin (ApiPlugin, SqlPlugin) rather than using the
    broker's ``plugin`` property.
    """

    plugin_class: type
    broker_module: str
    apply_builds_plugin: bool = False

    def _patch_broker_property(self, name: str, value) -> MagicMock:
        patcher = patch.object(self.SAMBrokerClass, name, new_callable=PropertyMock, return_value=value)  # type: ignore[attr-defined]
        mock = patcher.start()
        self.addCleanup(patcher.stop)  # type: ignore[attr-defined]
        return mock

    def _plugin_meta(self) -> MagicMock:
        plugin_meta = MagicMock(spec=PluginMeta)
        plugin_meta.name = "edge_case_plugin"
        return plugin_meta

    def _ready_broker(self, plugin=None, plugin_meta: Optional[MagicMock] = None, staff: bool = True):
        """Return the broker, with its user, plugin and plugin_meta replaced."""
        broker = self.broker  # type: ignore[attr-defined]
        self._patch_broker_property("user", MagicMock(is_staff=staff))
        if plugin is not None:
            if self.apply_builds_plugin and isinstance(plugin, self.plugin_class):
                patcher = patch(f"{self.broker_module}.{self.plugin_class.__name__}", type(plugin))
                patcher.start()
                self.addCleanup(patcher.stop)  # type: ignore[attr-defined]
            self._patch_broker_property("plugin", plugin)
        self._patch_broker_property("plugin_meta", plugin_meta)
        for name in ("to_json", "cache_invalidations", "verify_no_dependencies"):
            patcher = patch.object(broker, name, return_value={})
            patcher.start()
            self.addCleanup(patcher.stop)  # type: ignore[attr-defined]
        return broker

    def _fake_plugin(self, **kwargs):
        return fake_plugin_class(self.plugin_class, **kwargs)()

    # -------------------------------------------------------------------------
    # apply()
    # -------------------------------------------------------------------------
    def test_apply_requires_an_authenticated_user(self):
        """Apply() refuses to run without a user."""
        if self.apply_builds_plugin:
            return
        broker = self.broker  # type: ignore[attr-defined]
        self._patch_broker_property("user", None)
        with self.assertRaises(SAMBrokerError):  # type: ignore[attr-defined]
            broker.apply(self.request, **self.kwargs)  # type: ignore[attr-defined]

    def test_apply_requires_an_admin(self):
        """Apply() refuses to run for a non-staff user."""
        if self.apply_builds_plugin:
            return
        broker = self._ready_broker(staff=False)
        with self.assertRaises(SAMBrokerError):  # type: ignore[attr-defined]
            broker.apply(self.request, **self.kwargs)  # type: ignore[attr-defined]

    def test_apply_requires_a_plugin(self):
        """Apply() raises when the broker has no plugin."""
        if self.apply_builds_plugin:
            return
        broker = self._ready_broker()
        self._patch_broker_property("plugin", None)
        with self.assertRaises(SAMPluginBrokerError):  # type: ignore[attr-defined]
            broker.apply(self.request, **self.kwargs)  # type: ignore[attr-defined]

    def test_apply_rejects_a_plugin_of_the_wrong_type(self):
        """Apply() raises when the plugin isn't the broker's plugin class."""
        if self.apply_builds_plugin:
            return
        broker = self._ready_broker(plugin=MagicMock(ready=False), plugin_meta=self._plugin_meta())
        with self.assertRaises(SAMPluginBrokerError):  # type: ignore[attr-defined]
            broker.apply(self.request, **self.kwargs)  # type: ignore[attr-defined]

    def test_apply_requires_plugin_meta(self):
        """Apply() raises when the plugin has no PluginMeta."""
        if self.apply_builds_plugin:
            return
        broker = self._ready_broker(plugin=self._fake_plugin(ready=False), plugin_meta=None)
        with self.assertRaises(SAMPluginBrokerError):  # type: ignore[attr-defined]
            broker.apply(self.request, **self.kwargs)  # type: ignore[attr-defined]

    def test_apply_rejects_a_missing_manifest(self):
        """Apply() raises when a plugin-building broker has no manifest."""
        if not self.apply_builds_plugin:
            return
        broker = self.broker  # type: ignore[attr-defined]
        self._patch_broker_property("manifest", None)
        self._patch_broker_property("plugin_meta", None)
        with self.assertRaises(SAMPluginBrokerError):  # type: ignore[attr-defined]
            broker.apply(self.request, **self.kwargs)  # type: ignore[attr-defined]

    def test_apply_creates_and_saves_an_unready_plugin(self):
        """Apply() creates, then saves, a plugin that wasn't ready."""
        plugin = self._fake_plugin(ready=False)
        broker = self._ready_broker(plugin=plugin, plugin_meta=self._plugin_meta())
        type(plugin).create = MagicMock(side_effect=lambda: setattr(type(plugin), "ready", True))
        response = broker.apply(self.request, **self.kwargs)  # type: ignore[attr-defined]
        self.assertEqual(response.status_code, HTTPStatus.OK)  # type: ignore[attr-defined]
        type(plugin).create.assert_called_once()
        type(plugin).save.assert_called_once()

    def test_apply_reports_a_create_failure(self):
        """Apply() returns an error response when create() raises."""
        plugin = self._fake_plugin(ready=False, create_error=ValueError("create failed"))
        broker = self._ready_broker(plugin=plugin, plugin_meta=self._plugin_meta())
        response = broker.apply(self.request, **self.kwargs)  # type: ignore[attr-defined]
        self.assertGreaterEqual(response.status_code, HTTPStatus.BAD_REQUEST)  # type: ignore[attr-defined]

    def test_apply_reports_a_save_failure(self):
        """Apply() returns an error response when save() raises."""
        plugin = self._fake_plugin(ready=False, save_error=ValueError("save failed"))
        broker = self._ready_broker(plugin=plugin, plugin_meta=self._plugin_meta())
        type(plugin).create = MagicMock(side_effect=lambda: setattr(type(plugin), "ready", True))
        response = broker.apply(self.request, **self.kwargs)  # type: ignore[attr-defined]
        self.assertGreaterEqual(response.status_code, HTTPStatus.BAD_REQUEST)  # type: ignore[attr-defined]

    def test_apply_reports_a_plugin_that_never_becomes_ready(self):
        """Apply() returns an error response when the plugin isn't ready after create()."""
        plugin = self._fake_plugin(ready=False)
        broker = self._ready_broker(plugin=plugin, plugin_meta=self._plugin_meta())
        response = broker.apply(self.request, **self.kwargs)  # type: ignore[attr-defined]
        self.assertGreaterEqual(response.status_code, HTTPStatus.BAD_REQUEST)  # type: ignore[attr-defined]
        type(plugin).save.assert_not_called()

    # -------------------------------------------------------------------------
    # delete()
    # -------------------------------------------------------------------------
    def test_delete_requires_an_authenticated_user(self):
        """Delete() refuses to run without a user."""
        broker = self.broker  # type: ignore[attr-defined]
        self._patch_broker_property("user", None)
        with self.assertRaises(SAMBrokerError):  # type: ignore[attr-defined]
            broker.delete(self.request, **self.kwargs)  # type: ignore[attr-defined]

    def test_delete_requires_an_admin(self):
        """Delete() refuses to run for a non-staff user."""
        broker = self._ready_broker(staff=False)
        with self.assertRaises(SAMBrokerError):  # type: ignore[attr-defined]
            broker.delete(self.request, **self.kwargs)  # type: ignore[attr-defined]

    def test_delete_rejects_a_plugin_of_the_wrong_type(self):
        """Delete() raises when the plugin isn't the broker's plugin class."""
        broker = self._ready_broker(plugin=MagicMock(), plugin_meta=self._plugin_meta())
        with self.assertRaises(SAMPluginBrokerError):  # type: ignore[attr-defined]
            broker.delete(self.request, **self.kwargs)  # type: ignore[attr-defined]

    def test_delete_requires_plugin_meta(self):
        """Delete() raises when the plugin has no PluginMeta."""
        broker = self._ready_broker(plugin=self._fake_plugin(), plugin_meta=None)
        with self.assertRaises(SAMPluginBrokerError):  # type: ignore[attr-defined]
            broker.delete(self.request, **self.kwargs)  # type: ignore[attr-defined]

    def test_delete_requires_a_ready_plugin(self):
        """Delete() raises when the plugin isn't ready."""
        broker = self._ready_broker(plugin=self._fake_plugin(ready=False), plugin_meta=self._plugin_meta())
        with self.assertRaises(SAMBrokerErrorNotReady):  # type: ignore[attr-defined]
            broker.delete(self.request, **self.kwargs)  # type: ignore[attr-defined]

    def test_delete_wraps_a_delete_failure(self):
        """Delete() raises SAMBrokerError when the plugin's delete() raises."""
        plugin = self._fake_plugin()
        type(plugin).delete = MagicMock(side_effect=ValueError("delete failed"))
        broker = self._ready_broker(plugin=plugin, plugin_meta=self._plugin_meta())
        with self.assertRaises(SAMBrokerError):  # type: ignore[attr-defined]
            broker.delete(self.request, **self.kwargs)  # type: ignore[attr-defined]

    def test_delete_deletes_a_ready_plugin(self):
        """Delete() deletes a ready plugin and returns ok."""
        plugin = self._fake_plugin()
        broker = self._ready_broker(plugin=plugin, plugin_meta=self._plugin_meta())
        response = broker.delete(self.request, **self.kwargs)  # type: ignore[attr-defined]
        self.assertEqual(response.status_code, HTTPStatus.OK)  # type: ignore[attr-defined]
        type(plugin).delete.assert_called_once()

    # -------------------------------------------------------------------------
    # ORM-to-Pydantic spec conversions, plugin data, readiness and caching.
    # These apply to the brokers that set ``spec_kind``: static, websearch, skill.
    # -------------------------------------------------------------------------
    spec_kind: Optional[str] = None

    def spec_methods(self):
        """Return the broker's spec data and spec conversion methods, resetting their caches."""
        broker = self.broker  # type: ignore[attr-defined]
        setattr(broker, f"_plugin_{self.spec_kind}_spec_data", None)
        setattr(broker, f"_plugin_{self.spec_kind}_spec", None)
        broker._plugin_data = None
        return (
            broker,
            getattr(broker, f"plugin_{self.spec_kind}_spec_data_orm2pydantic"),
            getattr(broker, f"plugin_{self.spec_kind}_spec_orm2pydantic"),
        )

    def test_spec_conversions_without_plugin_meta(self):
        """Without a PluginMeta there's no plugin data, spec data or spec."""
        if not self.spec_kind:
            return
        broker, spec_data, spec = self.spec_methods()
        self._patch_broker_property("plugin_meta", None)
        self.assertIsNone(broker.plugin_data)  # type: ignore[attr-defined]
        self.assertIsNone(spec_data())  # type: ignore[attr-defined]
        self.assertIsNone(spec())  # type: ignore[attr-defined]

    def test_spec_conversions_without_plugin_data(self):
        """Without plugin data there's no spec data, so building the spec raises."""
        if not self.spec_kind:
            return
        broker, spec_data, spec = self.spec_methods()
        self._patch_broker_property("plugin_meta", self._plugin_meta())
        self._patch_broker_property("plugin_data", None)
        for name in ("plugin_prompt_orm2pydantic", "plugin_selector_orm2pydantic"):
            patcher = patch.object(broker, name, return_value=MagicMock())
            patcher.start()
            self.addCleanup(patcher.stop)  # type: ignore[attr-defined]
        data = spec_data()
        if data is None:
            with self.assertRaises(SAMPluginBrokerError):  # type: ignore[attr-defined]
                spec()
        else:
            # a static plugin's spec data is empty, rather than missing, without plugin data.
            self.assertFalse(data.model_dump(exclude_none=True).get("staticData"))  # type: ignore[attr-defined]

    def test_plugin_data_does_not_exist(self):
        """Plugin data that doesn't exist is None."""
        if not self.spec_kind:
            return
        broker, _, _ = self.spec_methods()
        self._patch_broker_property("plugin_meta", self._plugin_meta())
        model = broker.ORMModelClass
        with patch.object(model, "get_cached_data_by_plugin", side_effect=model.DoesNotExist):
            self.assertIsNone(broker.plugin_data)

    def test_ready_needs_the_base_broker(self):
        """The broker isn't ready when the plugin base broker isn't."""
        if not self.spec_kind:
            return
        broker = self.broker  # type: ignore[attr-defined]
        with patch.object(SAMPluginBaseBroker, "ready", new_callable=PropertyMock, return_value=False):
            self.assertFalse(broker.ready)

    def test_cached_manifest_of_the_wrong_type(self):
        """A cached manifest of the wrong type is rejected."""
        if not self.spec_kind:
            return
        broker = self.broker  # type: ignore[attr-defined]
        broker._manifest = {"kind": "Wrong"}
        with self.assertRaises(SAMPluginBrokerError):  # type: ignore[attr-defined]
            _ = broker.manifest

    def test_cache_invalidations(self):
        """Cache_invalidations() runs for a broker whose plugin may not be saved."""
        broker = self.broker  # type: ignore[attr-defined]
        self.assertIsNone(broker.cache_invalidations())

    def test_plugin_init_resets_the_broker(self):
        """Plugin_init() forgets the manifest, plugin and plugin data."""
        if not self.spec_kind:
            return
        broker = self.broker  # type: ignore[attr-defined]
        broker.plugin_init()
        self.assertIsNone(broker._manifest)  # type: ignore[attr-defined]
        self.assertIsNone(broker._plugin)  # type: ignore[attr-defined]
        self.assertIsNone(broker._plugin_data)  # type: ignore[attr-defined]

    def test_init_without_a_loader_manifest_or_plugin(self):
        """A broker with nothing to initialize from isn't ready."""
        if not self.spec_kind:
            return
        with patch.object(self.SAMBrokerClass, "ready", new_callable=PropertyMock, return_value=False):  # type: ignore[attr-defined]
            with patch.object(self.SAMBrokerClass, "plugin", new_callable=PropertyMock, return_value=None):  # type: ignore[attr-defined]
                broker = self.SAMBrokerClass(self.request)  # type: ignore[attr-defined]
        self.assertIsNone(broker._manifest)

    # -------------------------------------------------------------------------
    # These apply to the brokers that set ``orm_spec_method``: api, sql.
    # -------------------------------------------------------------------------
    orm_spec_method: Optional[str] = None

    def test_orm_conversions_without_plugin_meta(self):
        """Without a PluginMeta there's no plugin data, data conversion or spec."""
        if not self.orm_spec_method:
            return
        broker = self.broker  # type: ignore[attr-defined]
        broker._plugin_data = None
        self._patch_broker_property("plugin_meta", None)
        self.assertIsNone(broker.plugin_data)
        self.assertIsNone(broker.plugin_data_orm2pydantic())
        self.assertIsNone(getattr(broker, self.orm_spec_method)())

    def test_orm_plugin_init_resets_the_broker(self):
        """Plugin_init() forgets the manifest, plugin and plugin data."""
        if not self.orm_spec_method:
            return
        broker = self.broker  # type: ignore[attr-defined]
        broker.plugin_init()
        self.assertIsNone(broker._manifest)
        self.assertIsNone(broker._plugin)
        self.assertIsNone(broker._plugin_data)

    def test_orm_cached_manifest_of_the_wrong_type(self):
        """A cached manifest of the wrong type is rejected."""
        if not self.orm_spec_method:
            return
        broker = self.broker  # type: ignore[attr-defined]
        broker._manifest = {"kind": "Wrong"}
        with self.assertRaises(SAMPluginBrokerError):  # type: ignore[attr-defined]
            _ = broker.manifest

    def test_manifest_from_the_orm(self):
        """Without a loader, the manifest is built from the applied plugin's ORM records."""
        if not self.orm_spec_method:
            return
        broker = self.broker  # type: ignore[attr-defined]
        response = broker.apply(self.request, **self.kwargs)  # type: ignore[attr-defined]
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))  # type: ignore[attr-defined]
        name = broker.manifest.metadata.name
        plugin_meta = broker.plugin_meta
        self.assertIsNotNone(plugin_meta)  # type: ignore[attr-defined]

        self._patch_broker_property("loader", None)
        broker._manifest = None
        broker._plugin_meta = plugin_meta
        manifest = broker.manifest
        self.assertIsInstance(manifest, self.SAMBrokerClass(self.request, self.loader).SAMModelClass)  # type: ignore[attr-defined]
        self.assertEqual(manifest.metadata.name, name)  # type: ignore[attr-defined]

    def test_manifest_without_a_loader_or_plugin_meta(self):
        """Without a loader or a PluginMeta, there's no manifest."""
        if not self.orm_spec_method:
            return
        broker = self.broker  # type: ignore[attr-defined]
        self._patch_broker_property("loader", None)
        broker._manifest = None
        broker._plugin_meta = None
        self.assertIsNone(broker.manifest)
