"""Test :mod:`smarter.apps.plugin.contract.models`."""

from typing import get_args

from smarter.apps.account.serializers import user_can_delete
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.plugin.contract.models import (
    PluginApiPluginClass,
    PluginApiPluginMeta,
)
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.serializers import PluginMetaSerializer


class TestPluginContractModels(TestAccountMixin):
    """Test the plugin contract's models against the serializer whose output they replace."""

    def setUp(self):
        super().setUp()
        self.plugin_meta = PluginMeta.objects.create(
            name="test_plugin_contract_models", user_profile=self.user_profile, plugin_class="static"
        )
        self.plugin_meta.tags.add("contract", "test")
        self.addCleanup(PluginMeta.objects.filter(pk=self.plugin_meta.pk).delete)

    def test_plugin_class_is_the_choices(self):
        self.assertEqual(list(get_args(PluginApiPluginClass)), [value for value, _ in PluginMeta.PLUGIN_CLASSES])

    def test_plugin_meta_is_the_serializers_output(self):
        """Without a user, the model is exactly the serializer's output, whose canDelete is false."""
        model = PluginApiPluginMeta.from_model(self.plugin_meta)
        self.assertEqual(model.model_dump(mode="json"), dict(PluginMetaSerializer(self.plugin_meta).data))
        self.assertIs(model.can_delete, False)
        self.assertEqual(sorted(model.tags), ["contract", "test"])

    def test_can_delete_is_the_users(self):
        """CanDelete is user_can_delete() for the user.

        A plugin without its plugin data can't be checked, so it's false.
        """
        self.assertEqual(
            PluginApiPluginMeta.from_model(self.plugin_meta, self.admin_user).can_delete,
            user_can_delete(self.plugin_meta, self.plugin_meta.kind.value, self.admin_user),
        )
        self.assertIs(PluginApiPluginMeta.from_model(self.plugin_meta, self.non_admin_user).can_delete, False)
