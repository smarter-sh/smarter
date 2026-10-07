# pylint: disable=wrong-import-position
"""
Test :mod:`smarter.apps.plugin.admin`.

Each plugin class has its own proxy model and ModelAdmin on the Smarter
restricted admin site. Visibility is determined by ownership and role, and
each ModelAdmin lists only its own plugin class.
"""

from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory

from smarter.apps.dashboard.admin import smarter_restricted_admin_site
from smarter.apps.plugin import admin as plugin_admin
from smarter.apps.plugin.manifest.models.skill_plugin.model import SAMSkillPlugin
from smarter.apps.plugin.models import (
    PluginDataStatic,
    PluginMeta,
    PluginSelectorHistory,
)
from smarter.apps.plugin.plugin.skill import SkillPlugin
from smarter.lib import logging

from .base_classes import STATIC_PLUGIN_NAME, PluginAppTestBase, get_test_data

logger = logging.getLogger(__name__)

SKILL_PLUGIN_NAME = "test_plugin_app_admin_skill_plugin"
REGISTRY = {
    plugin_admin.PluginMetaStatic: plugin_admin.PluginStaticAdmin,
    plugin_admin.PluginMetaApi: plugin_admin.PluginApiAdmin,
    plugin_admin.PluginMetaSql: plugin_admin.PluginSqlAdmin,
    plugin_admin.PluginMetaSkill: plugin_admin.PluginSkillAdmin,
    plugin_admin.PluginMetaWebsearch: plugin_admin.PluginWebsearchAdmin,
    PluginSelectorHistory: plugin_admin.PluginSelectionHistoryAdmin,
}


class TestPluginAdmin(PluginAppTestBase):
    """
    Test the plugin ModelAdmins.

    In addition to the class fixture ``static_plugin``, a SkillPlugin owned by
    the admin user verifies that each ModelAdmin lists only its plugin class.
    """

    skill_plugin: SkillPlugin

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        data = get_test_data("skill-plugin.yaml")
        data["metadata"]["name"] = SKILL_PLUGIN_NAME
        cls.skill_plugin = SkillPlugin(manifest=SAMSkillPlugin(**data), user_profile=cls.user_profile)

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()

    def request(self, user=None):
        """Return a GET request for the admin site, by ``user``, which defaults to the admin user."""
        request = self.factory.get("/admin/")
        request.user = user or self.admin_user
        return request

    def model_admin(self, model):
        """Return the ModelAdmin that is registered for ``model``."""
        return smarter_restricted_admin_site._registry[model]  # pylint: disable=W0212

    def names(self, model, user=None) -> list[str]:
        """Return the names of the plugins that the ModelAdmin for ``model`` lists for ``user``."""
        return [plugin_meta.name for plugin_meta in self.model_admin(model).get_queryset(self.request(user))]

    def test_registered(self):
        """Test that each plugin class's proxy model is registered with its ModelAdmin."""
        for model, admin_class in REGISTRY.items():
            self.assertIn(model, smarter_restricted_admin_site._registry)  # pylint: disable=W0212
            self.assertIsInstance(self.model_admin(model), admin_class)

    def test_proxy_models(self):
        """Test that the plugin class models are proxies of PluginMeta."""
        for model in (
            plugin_admin.PluginMetaStatic,
            plugin_admin.PluginMetaApi,
            plugin_admin.PluginMetaSql,
            plugin_admin.PluginMetaSkill,
            plugin_admin.PluginMetaWebsearch,
        ):
            self.assertTrue(model._meta.proxy)  # pylint: disable=W0212
            self.assertTrue(issubclass(model, PluginMeta))

    def test_static_admin_queryset(self):
        """Test that the StaticPlugin admin lists the owner's static plugins, and not their skill plugins."""
        names = self.names(plugin_admin.PluginMetaStatic)
        self.assertIn(STATIC_PLUGIN_NAME, names)
        self.assertNotIn(SKILL_PLUGIN_NAME, names)

    def test_skill_admin_queryset(self):
        """Test that the SkillPlugin admin lists the owner's skill plugins, and not their static plugins."""
        names = self.names(plugin_admin.PluginMetaSkill)
        self.assertIn(SKILL_PLUGIN_NAME, names)
        self.assertNotIn(STATIC_PLUGIN_NAME, names)

    def test_other_admin_querysets(self):
        """Test that the Api, Sql and Websearch plugin admins list neither plugin."""
        for model in (plugin_admin.PluginMetaApi, plugin_admin.PluginMetaSql, plugin_admin.PluginMetaWebsearch):
            names = self.names(model)
            self.assertNotIn(STATIC_PLUGIN_NAME, names, model.__name__)
            self.assertNotIn(SKILL_PLUGIN_NAME, names, model.__name__)

    def test_anonymous_user_queryset(self):
        """Test that an anonymous user sees no plugins."""
        for model in REGISTRY:
            self.assertFalse(self.model_admin(model).get_queryset(self.request(AnonymousUser())).exists())

    def test_non_admin_user_queryset(self):
        """Test that a non-admin user does not administer the admin user's plugins."""
        self.assertNotIn(STATIC_PLUGIN_NAME, self.names(plugin_admin.PluginMetaStatic, user=self.non_admin_user))

    def test_selector_history_queryset(self):
        """Test that the selection history admin lists the history of the user's plugins."""
        history = PluginSelectorHistory.objects.create(
            plugin_selector=self.static_plugin.plugin_selector, search_term="Gobstopper", messages=[]
        )
        self.addCleanup(history.delete)
        model_admin = self.model_admin(PluginSelectorHistory)
        self.assertIn(history, model_admin.get_queryset(self.request()))
        self.assertNotIn(history, model_admin.get_queryset(self.request(self.non_admin_user)))
        self.assertFalse(model_admin.get_queryset(self.request(AnonymousUser())).exists())

    def test_plugin_name(self):
        """Test that plugin_name() separates the words of a camel cased name."""
        model_admin = self.model_admin(plugin_admin.PluginMetaStatic)
        self.assertEqual(model_admin.plugin_name(PluginMeta(name="EverlastingGobstopper")), "Everlasting Gobstopper")
        self.assertEqual(model_admin.plugin_name(PluginMeta(name="gobstopper")), "gobstopper")

    def test_readonly_fields(self):
        """Test that the plugin admins, and their inlines, are read only."""
        request = self.request()
        field_names = [field.name for field in PluginMeta._meta.fields]  # pylint: disable=W0212
        self.assertEqual(self.model_admin(plugin_admin.PluginMetaStatic).get_readonly_fields(request), field_names)
        inline = plugin_admin.PluginDataInline(PluginMeta, smarter_restricted_admin_site)
        self.assertEqual(
            inline.get_readonly_fields(request),
            [field.name for field in PluginDataStatic._meta.fields],  # pylint: disable=W0212
        )

    def test_changelist(self):
        """Test that the admin user can open the StaticPlugin changelist, which lists their plugin."""
        client = Client()
        client.force_login(self.admin_user)
        self.addCleanup(client.logout)
        response = client.get("/admin/plugin/pluginmetastatic/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(STATIC_PLUGIN_NAME, response.content.decode())
