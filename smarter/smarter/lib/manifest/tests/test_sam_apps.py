"""Test :mod:`smarter.lib.manifest.sam_apps`, the SAM resource apps' feature flags."""

from smarter_types import SAMKinds

from smarter.apps.guardrail import urls as guardrail_urls
from smarter.apps.guardrail.const import namespace as guardrail_namespace
from smarter.apps.guardrail.urls import GuardrailReverseNames
from smarter.apps.secret import urls as secret_urls
from smarter.apps.secret.const import namespace as secret_namespace
from smarter.common.conf import smarter_settings
from smarter.common.conf.settings import Settings
from smarter.common.mixins.helper_mixin import SmarterReadyState
from smarter.lib.manifest.sam_apps import (
    CORE_KINDS,
    SAM_APPS,
    SamAppUrls,
    SAMKindDisabledError,
    get_sam_app,
    kind_is_enabled,
    raise_if_kind_disabled,
    reverse_if_enabled,
    sam_app_of_kind,
    sam_app_urlpatterns,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

APPS_URLS = [
    SamAppUrls("app_guardrail_enable", "Guardrail", "guardrail/", guardrail_urls, guardrail_namespace),
    SamAppUrls("app_secret_enable", "Secret", "secret/", secret_urls, secret_namespace),
]


def disabled(*settings: str) -> Settings:
    """Return a copy of ``smarter_settings`` with these flags false."""
    update = {}
    for setting in settings:
        update[setting] = False
    return smarter_settings.model_copy(update=update)


class TestSamApps(SmarterTestBase):
    """Test the table of SAM apps, and the lookups by kind."""

    def test_every_kind_has_one_owner(self):
        """Test that every SAM kind is either a core kind or the kind of exactly one SAM app."""
        for kind in SAMKinds.all():
            owners = []
            for sam_app in SAM_APPS:
                if kind in sam_app.kinds:
                    owners.append(sam_app.app_label)
            with self.subTest(kind=kind):
                if kind in CORE_KINDS:
                    self.assertEqual(owners, [])
                else:
                    self.assertEqual(len(owners), 1, owners)

    def test_every_flag_is_a_setting_that_defaults_to_true(self):
        """Test that each app's flag is a Settings field, true by default, and named after the app."""
        for sam_app in SAM_APPS:
            with self.subTest(app=sam_app.app_label):
                self.assertEqual(sam_app.setting, f"app_{sam_app.app_label}_enable")
                self.assertIs(Settings.model_fields[sam_app.setting].default, True)
                self.assertTrue(sam_app.is_enabled(smarter_settings))

    def test_env_name(self):
        self.assertEqual(get_sam_app("app_guardrail_enable").env_name, "SMARTER_APP_GUARDRAIL_ENABLE")

    def test_get_sam_app_unknown(self):
        with self.assertRaises(KeyError):
            get_sam_app("enable_nothing")

    def test_sam_app_of_kind(self):
        """Test that the lookup by kind ignores case, and that a core or unknown kind has no app."""
        self.assertEqual(sam_app_of_kind("SqlPlugin").app_label, "llmtool")  # type: ignore[union-attr]
        self.assertEqual(sam_app_of_kind("customdomain").app_label, "llmclient")  # type: ignore[union-attr]
        self.assertIsNone(sam_app_of_kind(SAMKinds.ACCOUNT.value))
        self.assertIsNone(sam_app_of_kind("NoSuchKind"))

    def test_kind_is_enabled(self):
        settings = disabled("app_guardrail_enable")
        self.assertFalse(kind_is_enabled("Guardrail", settings))
        self.assertTrue(kind_is_enabled("Secret", settings))
        self.assertTrue(kind_is_enabled(SAMKinds.USER.value, settings))
        self.assertTrue(kind_is_enabled("Guardrail"))

    def test_raise_if_kind_disabled(self):
        """Test that a disabled kind raises, with the environment variable that enables it."""
        settings = disabled("app_llmtool_enable")
        with self.assertRaises(SAMKindDisabledError) as context:
            raise_if_kind_disabled(SAMKinds.STATIC_PLUGIN.value, settings)
        self.assertIn("SMARTER_APP_LLMTOOL_ENABLE=true", str(context.exception))
        raise_if_kind_disabled(SAMKinds.STATIC_PLUGIN.value)
        raise_if_kind_disabled(SAMKinds.PROMPT.value, settings)

    def test_reverse_if_enabled(self):
        url = reverse_if_enabled(
            "app_guardrail_enable", GuardrailReverseNames.namespace, GuardrailReverseNames.listview
        )
        self.assertIsInstance(url, str)


class TestSamAppUrlpatterns(SmarterTestBase):
    """Test that the url patterns follow the apps' flags."""

    def test_all_enabled(self):
        patterns = sam_app_urlpatterns(smarter_settings, APPS_URLS, "test urls")
        namespaces = [pattern.namespace for pattern in patterns]
        self.assertEqual(namespaces, [guardrail_namespace, secret_namespace])

    def test_one_disabled(self):
        """Test that a false flag leaves out that app's urls, and logs how to enable them."""
        settings = disabled("app_guardrail_enable")
        with self.assertLogs("smarter.lib.manifest.sam_apps", level="INFO") as logs:
            patterns = sam_app_urlpatterns(settings, APPS_URLS, "test urls")
        namespaces = [pattern.namespace for pattern in patterns]
        self.assertEqual(namespaces, [secret_namespace])
        output = "\n".join(logs.output)
        self.assertIn("Guardrail test urls is", output)
        self.assertIn("SMARTER_APP_GUARDRAIL_ENABLE=true", output)

    def test_logs_are_named_after_the_caller(self):
        """Test that each READY line names the module that mounts the urls, not this helper."""
        with self.assertLogs("smarter.lib.manifest.sam_apps", level="DEBUG") as logs:
            sam_app_urlpatterns(smarter_settings, APPS_URLS, "test urls")
        ready = [
            record.getMessage() for record in logs.records if f"is {SmarterReadyState.READY}" in record.getMessage()
        ]
        self.assertEqual(len(ready), 2)
        for message in ready:
            self.assertIn(__name__, message)
            self.assertNotIn("sam_app_urlpatterns", message)
        self.assertTrue(all(record.pathname == __file__ for record in logs.records))

    def test_all_disabled(self):
        settings = disabled("app_guardrail_enable", "app_secret_enable")
        patterns = sam_app_urlpatterns(settings, APPS_URLS, "test urls")
        self.assertEqual(patterns, [])
