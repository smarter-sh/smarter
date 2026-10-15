"""Tests of smarter.apps.llmtool.extension.installer, with its lifecycle hooks and resources."""

from unittest.mock import patch

from waffle.models import Switch

from smarter.apps.llmtool.extension import installer as installer_module
from smarter.apps.llmtool.extension.exceptions import (
    SmarterExtensionInstallError,
    SmarterExtensionLoadError,
)
from smarter.apps.llmtool.extension.lifecycle import LifecycleContext
from smarter.apps.llmtool.extension.resources import (
    apply_extension_manifest,
    delete_extension_resource,
)
from smarter.apps.llmtool.models import (
    Extension,
    ExtensionResource,
    ExtensionSetting,
    ExtensionTrustBadge,
    ExtensionVersion,
)
from smarter.apps.llmtool.signals import (
    extension_disabled,
    extension_installed,
    extension_uninstalled,
    extension_upgraded,
)
from smarter.apps.secret.models import Secret

from .mixins import ECHO_SECRET, ExtensionTestMixin, fixture_archive

SWITCH = "ext_echo_verbose"


class TestInstall(ExtensionTestMixin):
    """Test installing extensions."""

    def test_install(self):
        """An install saves the version, creates switches and resources, runs hooks, and leaves it disabled."""
        received = []
        extension_installed.connect(lambda **kwargs: received.append(kwargs), weak=False, dispatch_uid="t1")
        try:
            extension = self.installer.install(fixture_archive("echo"))
        finally:
            extension_installed.disconnect(dispatch_uid="t1")
        self.assertFalse(extension.enabled)
        self.assertEqual(extension.display_name, "Echo")
        self.assertEqual(extension.trust_badge, ExtensionTrustBadge.UNVERIFIED)
        self.assertEqual(extension.publisher, "Smarter Team <test@example.com>")
        version = extension.installed_version
        self.assertEqual(version.version, "1.0.0")  # type: ignore[union-attr]
        self.assertIn("Echoes what it is sent", version.docstring)  # type: ignore[union-attr]
        self.assertIn("<p>", version.docs_html)  # type: ignore[union-attr]
        self.assertEqual(version.installed_by, self.admin_user)  # type: ignore[union-attr]
        self.assertTrue(Switch.objects.filter(name=SWITCH, active=False).exists())
        self.assertTrue(Secret.objects.filter(name=ECHO_SECRET).exists())
        self.assertEqual(
            list(extension.resources.values_list("kind", "name", "managed")), [("Secret", ECHO_SECRET, True)]
        )
        self.assertEqual(len(received), 1)
        self.assertEqual(str(extension), "Echo (echo 1.0.0)")
        self.assertEqual(str(version), "echo 1.0.0")

    def test_hooks_run_in_order(self):
        """Pre_install runs before the version is saved, post_install after its resources."""
        calls = []

        def pre_install(_self, context: LifecycleContext):
            calls.append(("pre", Secret.objects.filter(name=ECHO_SECRET).exists()))

        def post_install(_self, context: LifecycleContext):
            calls.append(("post", Secret.objects.filter(name=ECHO_SECRET).exists()))

        archive = fixture_archive("echo")
        loaded = installer_module.load_archive(installer_module.ExtensionArchive(archive))
        with (
            patch.object(loaded.lifecycle, "pre_install", pre_install),
            patch.object(loaded.lifecycle, "post_install", post_install),
        ):
            self.installer.install(archive)
        self.assertEqual(calls, [("pre", False), ("post", True)])

    def test_reinstall_same_archive(self):
        """Installing the installed version again, from the same archive, does nothing."""
        extension = self.install_echo()
        again = self.installer.install(fixture_archive("echo"))
        self.assertEqual(again.pk, extension.pk)
        self.assertEqual(self.echo_hooks(extension)["CALLS"], [])

    def test_same_version_different_archive(self):
        """A released version cannot be replaced by a different archive."""
        self.install_echo()
        with self.assertRaisesRegex(SmarterExtensionInstallError, "different archive"):
            self.installer.install(fixture_archive("echo", without=("README.md",)))

    def test_incompatible(self):
        """An incompatible extension is refused before anything is saved."""
        with self.assertRaisesRegex(SmarterExtensionInstallError, "not compatible"):
            self.installer.install(fixture_archive("incompatible"))
        self.assertFalse(Extension.objects.filter(slug="incompatible").exists())

    def test_broken(self):
        """An extension whose code does not load is refused before anything is saved."""
        with self.assertRaises(SmarterExtensionLoadError):
            self.installer.install(fixture_archive("broken"))
        self.assertFalse(Extension.objects.filter(slug="broken").exists())

    def test_pre_install_refuses(self):
        """A pre_install hook that raises rolls the install back."""
        archive = fixture_archive("echo")
        loaded = installer_module.load_archive(installer_module.ExtensionArchive(archive))
        loaded.entry_point("echo.lifecycle:FAIL").add("pre_install")
        try:
            with self.assertRaisesRegex(RuntimeError, "pre_install failed"):
                self.installer.install(archive)
        finally:
            loaded.entry_point("echo.lifecycle:FAIL").clear()
        self.assertFalse(Extension.objects.filter(slug="echo").exists())
        self.assertFalse(ExtensionVersion.objects.filter(extension__slug="echo").exists())

    def test_post_install_fails(self):
        """A post_install hook that raises leaves the extension installed, disabled, with the error."""
        archive = fixture_archive("echo")
        loaded = installer_module.load_archive(installer_module.ExtensionArchive(archive))
        loaded.entry_point("echo.lifecycle:FAIL").add("post_install")
        try:
            extension = self.installer.install(archive)
        finally:
            loaded.entry_point("echo.lifecycle:FAIL").clear()
        extension.refresh_from_db()
        self.assertFalse(extension.enabled)
        self.assertIn("post_install failed", extension.error)
        self.assertIsNotNone(extension.installed_version)

    def test_registry_metadata(self):
        """The source, trust badge, publisher and url of a registry install are recorded."""
        extension = self.installer.install(
            fixture_archive("echo"),
            source="registry",
            trust_badge=ExtensionTrustBadge.OFFICIAL,
            publisher="smarter-sh",
            source_url="https://example.com/echo-1.0.0.zip",
        )
        self.assertEqual(
            (extension.source, extension.trust_badge, extension.publisher), ("registry", "official", "smarter-sh")
        )
        self.assertEqual(extension.installed_version.source_url, "https://example.com/echo-1.0.0.zip")  # type: ignore[union-attr]


class TestUpgrade(ExtensionTestMixin):
    """Test updating and rolling back extensions."""

    def test_upgrade(self):
        """An update keeps the old version, runs the upgrade hooks, and deletes resources the new version dropped."""
        extension = self.enable_echo()
        received = []
        extension_upgraded.connect(lambda **kwargs: received.append(kwargs), weak=False, dispatch_uid="t2")
        try:
            extension = self.installer.install(fixture_archive("echo", version="1.1.0", without=("echo/manifests",)))
        finally:
            extension_upgraded.disconnect(dispatch_uid="t2")
        self.assertEqual(extension.installed_version.version, "1.1.0")  # type: ignore[union-attr]
        self.assertTrue(extension.enabled)
        self.assertEqual(extension.versions.count(), 2)
        self.assertFalse(Secret.objects.filter(name=ECHO_SECRET).exists())
        self.assertFalse(extension.resources.exists())
        self.assertEqual(received[0]["previous_version"], "1.0.0")
        calls = self.echo_hooks(extension)["CALLS"]
        self.assertEqual(calls, [("pre_upgrade", "1.1.0", "1.0.0"), ("post_upgrade", "1.1.0", "1.0.0")])
        self.assertFalse(extension.update_available)
        extension.latest_version = "2.0.0"
        self.assertTrue(extension.update_available)
        extension.latest_version = "not a version"
        self.assertFalse(extension.update_available)

    def test_upgrade_disables_when_settings_missing(self):
        """An enabled extension whose new version needs settings that are not configured is disabled."""
        extension = self.enable_echo()
        ExtensionSetting.objects.filter(extension=extension, name="api_key").delete()
        extension = self.installer.install(fixture_archive("echo", version="1.1.0"))
        extension.refresh_from_db()
        self.assertFalse(extension.enabled)
        self.assertIn("api_key", extension.error)

    def test_rollback(self):
        """Rolling back makes an earlier version the installed one."""
        extension = self.install_echo()
        old = extension.installed_version
        extension = self.installer.install(fixture_archive("echo", version="1.1.0"))
        extension = self.installer.rollback(extension, old)  # type: ignore[arg-type]
        self.assertEqual(extension.installed_version.version, "1.0.0")  # type: ignore[union-attr]
        self.assertEqual(extension.versions.count(), 2)

    def test_rollback_other_extension(self):
        """A version of another extension cannot be rolled back to."""
        extension = self.install_echo()
        other = Extension.objects.create(slug="broken", display_name="Broken")
        with self.assertRaises(SmarterExtensionInstallError):
            self.installer.rollback(other, extension.installed_version)  # type: ignore[arg-type]


class TestConfigureEnableDisable(ExtensionTestMixin):
    """Test configuring, enabling and disabling extensions."""

    def test_configure(self):
        """Settings are validated, stored as text, and cleared with None."""
        extension = self.install_echo()
        self.installer.configure(extension, {"repeat": 2, "greeting": "hi"})
        self.assertEqual(ExtensionSetting.objects.get(extension=extension, name="repeat").value, "2")
        self.installer.configure(extension, {"greeting": None})
        self.assertFalse(ExtensionSetting.objects.filter(extension=extension, name="greeting").exists())
        for values, message in (
            ({"nope": "x"}, "no setting"),
            ({"repeat": "many"}, "repeat"),
            ({"api_key": "plain text"}, "must be a Secret"),
            ({"repeat": self.secret("echo_wrong_secret")}, "not a secret setting"),
        ):
            with self.subTest(values=values):
                with self.assertRaisesRegex(SmarterExtensionInstallError, message):
                    self.installer.configure(extension, values)

    def test_enable_requires_settings(self):
        """An extension cannot be enabled while required settings are missing."""
        extension = self.install_echo()
        with self.assertRaisesRegex(SmarterExtensionInstallError, "api_key"):
            self.installer.enable(extension)

    def test_enable_and_disable(self):
        """Enabling and disabling run their hooks and send signals."""
        extension = self.enable_echo()
        self.assertTrue(extension.enabled)
        received = []
        extension_disabled.connect(lambda **kwargs: received.append(kwargs), weak=False, dispatch_uid="t3")
        try:
            self.installer.disable(extension)
        finally:
            extension_disabled.disconnect(dispatch_uid="t3")
        self.assertFalse(Extension.objects.get(pk=extension.pk).enabled)
        self.assertEqual(received[0]["reason"], "disabled by an administrator")
        hooks = [call[0] for call in self.echo_hooks(extension)["CALLS"]]
        self.assertEqual(hooks, ["on_enable", "on_disable"])

    def test_on_enable_refuses(self):
        """An on_enable hook that raises keeps the extension disabled."""
        extension = self.install_echo()
        self.installer.configure(extension, {"api_key": self.secret("echo_refuse_key")})
        self.echo_hooks(extension)["FAIL"].add("on_enable")
        with self.assertRaisesRegex(RuntimeError, "on_enable failed"):
            self.installer.enable(extension)
        self.assertFalse(Extension.objects.get(pk=extension.pk).enabled)

    def test_on_disable_fails(self):
        """An on_disable hook that raises is logged, and the extension is disabled anyway."""
        extension = self.enable_echo()
        self.echo_hooks(extension)["FAIL"].add("on_disable")
        self.installer.disable(extension)
        self.assertFalse(Extension.objects.get(pk=extension.pk).enabled)

    def test_not_installed(self):
        """An extension without an installed version cannot be configured or enabled."""
        extension = Extension.objects.create(slug="broken", display_name="Broken")
        with self.assertRaisesRegex(SmarterExtensionInstallError, "no installed version"):
            self.installer.enable(extension)
        self.installer.disable(extension)

    def test_enable_incompatible(self):
        """An installed extension that is no longer compatible cannot be enabled."""
        extension = self.install_echo()
        self.installer.configure(extension, {"api_key": self.secret("echo_incompatible_key")})
        with patch.object(installer_module.ExtensionManifest, "compatibility_problems", return_value=["too old"]):
            with self.assertRaisesRegex(SmarterExtensionInstallError, "too old"):
                self.installer.enable(extension)


class TestUninstall(ExtensionTestMixin):
    """Test uninstalling extensions."""

    def test_uninstall(self):
        """Uninstalling deletes the extension's resources, switches, settings and versions, and runs its hooks."""
        extension = self.enable_echo()
        hooks = self.echo_hooks(extension)
        received = []
        extension_uninstalled.connect(lambda **kwargs: received.append(kwargs), weak=False, dispatch_uid="t4")
        try:
            self.installer.uninstall(extension)
        finally:
            extension_uninstalled.disconnect(dispatch_uid="t4")
        self.assertFalse(Extension.objects.filter(slug="echo").exists())
        self.assertFalse(ExtensionVersion.objects.filter(extension__slug="echo").exists())
        self.assertFalse(ExtensionSetting.objects.filter(extension__slug="echo").exists())
        self.assertFalse(Switch.objects.filter(name=SWITCH).exists())
        self.assertFalse(Secret.objects.filter(name=ECHO_SECRET).exists())
        self.assertEqual(
            received, [{"signal": extension_uninstalled, "sender": installer_module.ExtensionInstaller, "slug": "echo"}]
        )
        self.assertEqual([call[0] for call in hooks["CALLS"]][-2:], ["pre_uninstall", "post_uninstall"])

    def test_pre_uninstall_refuses(self):
        """A pre_uninstall hook that raises cancels the uninstall."""
        extension = self.install_echo()
        self.echo_hooks(extension)["FAIL"].add("pre_uninstall")
        with self.assertRaisesRegex(SmarterExtensionInstallError, "refused"):
            self.installer.uninstall(extension)
        self.assertTrue(Extension.objects.filter(slug="echo").exists())
        self.echo_hooks(extension)["FAIL"].clear()

    def test_post_uninstall_fails(self):
        """A post_uninstall hook that raises is logged, and the uninstall finishes."""
        extension = self.install_echo()
        self.echo_hooks(extension)["FAIL"].add("post_uninstall")
        try:
            self.installer.uninstall(extension)
        finally:
            self.echo_hooks_clear_after_uninstall()
        self.assertFalse(Extension.objects.filter(slug="echo").exists())

    def echo_hooks_clear_after_uninstall(self):
        """Clear FAIL in every loaded copy of the echo lifecycle module."""
        # pylint: disable=import-outside-toplevel
        import sys

        for name, module in list(sys.modules.items()):
            if name.startswith("smarter_extensions.echo.") and name.endswith(".lifecycle"):
                module.FAIL.clear()  # type: ignore[attr-defined]

    def test_uninstall_broken_code(self):
        """An extension whose code no longer loads is uninstalled without its hooks."""
        extension = self.install_echo()
        with patch.object(installer_module, "load_version", side_effect=SmarterExtensionLoadError("gone")):
            self.installer.uninstall(extension)
        self.assertFalse(Extension.objects.filter(slug="echo").exists())


class TestResources(ExtensionTestMixin):
    """Test the SAM resources that extensions create."""

    def test_apply_and_delete(self):
        """A lifecycle hook's manifest is applied, recorded as unmanaged, and deleted with the extension."""
        extension = self.install_echo()
        manifest = (
            "apiVersion: smarter.sh/v1\nkind: Secret\nmetadata:\n  name: echo_hook_secret\n"
            "  description: x\n  version: 1.0.0\nspec:\n  config:\n    value: x\n"
        )
        context = self.installer.context(extension, extension.installed_version.parsed_manifest)  # type: ignore[union-attr]
        self.assertEqual(context.slug, "echo")
        self.assertEqual(context.apply_manifest(manifest), ("Secret", "echo_hook_secret"))
        self.assertTrue(
            ExtensionResource.objects.filter(extension=extension, name="echo_hook_secret", managed=False).exists()
        )
        context.delete_resource("Secret", "echo_hook_secret")
        self.assertFalse(Secret.objects.filter(name="echo_hook_secret").exists())
        self.assertFalse(ExtensionResource.objects.filter(name="echo_hook_secret").exists())

    def test_invalid_manifests(self):
        """Manifests that are not valid, of unknown kinds, or that brokers refuse, are errors."""
        extension = self.install_echo()
        owner = self.installer.owner
        with self.assertRaisesRegex(SmarterExtensionInstallError, "not valid"):
            apply_extension_manifest(extension, "{not: [valid", owner, "1.0.0")
        with self.assertRaisesRegex(SmarterExtensionInstallError, "no SAM kind"):
            apply_extension_manifest(
                extension, "apiVersion: smarter.sh/v1\nkind: Nope\nmetadata:\n  name: x\nspec: {}\n", owner, "1.0.0"
            )
        with self.assertRaisesRegex(SmarterExtensionInstallError, "could not apply"):
            apply_extension_manifest(
                extension, "apiVersion: smarter.sh/v1\nkind: Secret\nmetadata:\n  name: x\nspec: {}\n", owner, "1.0.0"
            )

    def test_delete_missing_resource(self):
        """Deleting a resource that no longer exists, or of an unknown kind, just forgets it."""
        extension = self.install_echo()
        owner = self.installer.owner
        ExtensionResource.objects.create(extension=extension, kind="Nope", name="x", user_profile=owner, version="1")
        delete_extension_resource(extension, "Nope", "x", owner)
        delete_extension_resource(extension, "Secret", "echo_never_existed", owner)
        self.assertFalse(ExtensionResource.objects.filter(extension=extension, kind="Nope").exists())
