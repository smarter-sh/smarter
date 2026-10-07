"""Test the built-in Proxies, :mod:`smarter.apps.proxy.builtins`, and ``manage.py add_builtin_proxies``."""

import inspect
import io
import os
import shutil
import tempfile
from unittest.mock import patch

import yaml
from django.core.management import call_command

from smarter.apps.account.management.commands import initialize_platform
from smarter.apps.proxy import builtins
from smarter.apps.proxy.builtins import add_builtin_proxies, builtin_manifest_files
from smarter.apps.proxy.const import BUILTIN_PROXY_PATH
from smarter.apps.proxy.models import Proxy

from .base_classes import PROVIDER_NAME, SECRET_NAME, ProxyTestBase, get_test_data


class TestBuiltinProxies(ProxyTestBase):
    """Test the application of the built-in Proxy manifests, from a directory of test manifests."""

    def setUp(self):
        super().setUp()
        self.path = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.path)
        self.addCleanup(Proxy.objects.filter(user_profile=self.user_profile, name__startswith="test_builtin").delete)

    def write(self, name: str, **spec_changes) -> str:
        """Write a manifest named name to the directory, from the test manifest, with spec changes."""
        manifest = get_test_data("proxy.yaml")
        manifest["metadata"]["name"] = name
        manifest["spec"].update(spec_changes)
        filename = os.path.join(self.path, f"{name}.yaml")
        with open(filename, "w", encoding="utf-8") as f:
            yaml.safe_dump(manifest, f)
        return filename

    def test_builtin_manifest_files(self):
        files = builtin_manifest_files()
        self.assertTrue(all(f.startswith(BUILTIN_PROXY_PATH) and f.endswith(".yaml") for f in files))
        self.assertIn(os.path.join(BUILTIN_PROXY_PATH, "openai.yaml"), files)
        self.assertEqual(files, sorted(files))

    def test_add_builtin_proxies(self):
        """Test that manifests are applied, those without a Provider or Secret skipped, and failures isolated."""
        self.write("test_builtin_applied", provider=PROVIDER_NAME, apiKey=SECRET_NAME)
        self.write("test_builtin_no_provider", provider="test_builtin_no_such_provider")
        self.write("test_builtin_no_secret", apiKey="test_builtin_no_such_secret")
        self.write("test_builtin_invalid", headers={"Authorization": "Bearer x"})
        result = add_builtin_proxies(user_profile=self.user_profile, path=self.path)
        self.assertEqual(result.applied, ["test_builtin_applied"])
        self.assertEqual(sorted(result.skipped), ["test_builtin_no_provider", "test_builtin_no_secret"])
        self.assertEqual(result.failed, ["test_builtin_invalid"])
        self.assertFalse(result.success)
        proxy = Proxy.objects.get(user_profile=self.user_profile, name="test_builtin_applied")
        self.assertEqual((proxy.provider, proxy.api_key_secret), (self.provider, self.secret))

    def test_idempotent(self):
        self.write("test_builtin_twice")
        self.assertTrue(add_builtin_proxies(user_profile=self.user_profile, path=self.path).success)
        self.assertTrue(add_builtin_proxies(user_profile=self.user_profile, path=self.path).success)
        self.assertEqual(Proxy.objects.filter(user_profile=self.user_profile, name="test_builtin_twice").count(), 1)

    def test_command(self):
        self.write("test_builtin_command")
        path = self.path

        def add_from_test_path(user_profile=None):
            return add_builtin_proxies(user_profile=user_profile, path=path)

        out = io.StringIO()
        with patch(
            "smarter.apps.proxy.management.commands.add_builtin_proxies.add_builtin_proxies", add_from_test_path
        ):
            call_command("add_builtin_proxies", username=self.admin_user.username, stdout=out)
        self.assertIn("Applied Proxy test_builtin_command.", out.getvalue())
        self.assertTrue(Proxy.objects.filter(user_profile=self.user_profile, name="test_builtin_command").exists())

    def test_initialize_platform(self):
        """Test that initialize_platform adds the built-in Proxies after the Providers that they use."""
        source = inspect.getsource(initialize_platform.Command.handle)
        self.assertIn('call_command("add_builtin_proxies")', source)
        self.assertLess(
            source.index('call_command("initialize_providers")'), source.index('call_command("add_builtin_proxies")')
        )

    def test_builtin_proxies(self):
        self.assertEqual(builtins.builtin_proxies().model, Proxy)
