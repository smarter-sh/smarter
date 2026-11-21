"""Test :mod:`smarter.lib.django.apps`, the base class of every Smarter app's AppConfig."""

from unittest.mock import patch

from django.apps import AppConfig, apps

from smarter.lib.django.apps import SmarterAppConfig
from smarter.lib.manifest.sam_apps import SAM_APPS
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.sam_apps import disabled_sam_apps

SMARTER_APPS_MODULE = "smarter.lib.django.apps"


def smarter_app_configs() -> list[AppConfig]:
    """Return the AppConfig of every installed Smarter app."""
    configs = []
    for app_config in apps.get_app_configs():
        if app_config.name.startswith("smarter."):
            configs.append(app_config)
    return configs


class TestSmarterAppConfig(SmarterTestBase):
    """Test that every Smarter app uses SmarterAppConfig, and that ready() follows the app's flag."""

    def test_every_smarter_app_has_its_own_config(self):
        """
        Test that Django uses each app's own AppConfig, not a plain AppConfig.

        Django falls back to a plain AppConfig, silently, when an apps.py holds more than one AppConfig
        subclass, e.g. when it imports SmarterAppConfig by name. Its ready() would then do nothing.
        """
        configs = smarter_app_configs()
        self.assertGreaterEqual(len(configs), 20)
        for app_config in configs:
            with self.subTest(app=app_config.label):
                self.assertIsInstance(app_config, SmarterAppConfig)
                self.assertIsNot(type(app_config), SmarterAppConfig)
                self.assertTrue(str(app_config.verbose_name).startswith("Smarter "))

    def test_every_sam_app_has_its_flag(self):
        """Test that each SAM app's AppConfig names its feature flag, and the core apps have none."""
        flags = {}
        for sam_app in SAM_APPS:
            flags[sam_app.app_label] = sam_app.setting
        for app_config in smarter_app_configs():
            with self.subTest(app=app_config.label):
                self.assertEqual(app_config.enabled_setting, flags.get(app_config.label))  # type: ignore[attr-defined]

    def test_ready_modules_exist(self):
        """Test that each app's ready modules can be imported."""
        for app_config in smarter_app_configs():
            for module in app_config.ready_modules:  # type: ignore[attr-defined]
                module_name = app_config.ready_module_name(module)  # type: ignore[attr-defined]
                with self.subTest(module=module_name):
                    self.assertTrue(module_name.startswith("smarter."))

    def test_enabled(self):
        """Test that an enabled app imports its modules and logs that it is ready."""
        app_config = apps.get_app_config("guardrail")
        with patch("importlib.import_module") as import_module:
            with self.assertLogs(SMARTER_APPS_MODULE, level="DEBUG") as logs:
                app_config.ready()
        imported = [call.args[0] for call in import_module.call_args_list]
        self.assertEqual(imported, ["smarter.apps.guardrail.receivers", "smarter.apps.guardrail.signals"])
        output = "\n".join(logs.output)
        self.assertIn("Smarter Guardrail app is", output)
        self.assertNotIn("NOT_READY", output)

    def test_disabled(self):
        """Test that a disabled SAM app imports nothing, and logs how to enable it."""
        for sam_app in SAM_APPS:
            app_config = apps.get_app_config(sam_app.app_label)
            with self.subTest(app=sam_app.app_label):
                with disabled_sam_apps(sam_app.setting, modules=(SMARTER_APPS_MODULE,)):
                    with patch("importlib.import_module") as import_module:
                        with self.assertLogs(SMARTER_APPS_MODULE, level="INFO") as logs:
                            app_config.ready()
                import_module.assert_not_called()
                output = "\n".join(logs.output)
                self.assertIn(f"{sam_app.env_name}=true", output)

    def test_core_app_is_always_enabled(self):
        """Test that a core app, which has no flag, is enabled."""
        app_config = apps.get_app_config("account")
        self.assertTrue(app_config.is_enabled())  # type: ignore[attr-defined]

    def test_on_ready(self):
        """Test that the prompt app registers its journal sources, in on_ready()."""
        app_config = apps.get_app_config("prompt")
        with patch("smarter.apps.prompt.journal.register") as register:
            app_config.ready()
        register.assert_called_once_with()
