"""Test that modules which nothing else imports still load, and that their contents are well formed: the per-app api/urls.py configurations that the project urlconf does not include, and the manifest enum modules that are kept for backward compatibility."""

import importlib
import inspect

from django.urls import URLPattern, URLResolver

from smarter.common.enum import SmarterEnumAbstract as CommonSmarterEnumAbstract
from smarter.lib.manifest.enum import SmarterEnumAbstract as ManifestSmarterEnumAbstract
from smarter.lib.unittest.base_classes import SmarterTestBase

API_URLCONFS = [
    "smarter.apps.account.api.urls",
    "smarter.apps.connection.api.urls",
    "smarter.apps.llmclient.api.urls",
    "smarter.apps.prompt.api.urls",
    "smarter.apps.proxy.api.urls",
    "smarter.apps.secret.api.urls",
    "smarter.apps.vectorstore.api.urls",
]

ENUM_MODULES = [
    "smarter.apps.connection.manifest.enum",
    "smarter.apps.llmclient.manifest.enum",
    "smarter.apps.plugin.manifest.models.common.plugin.enum",
    "smarter.apps.proxy.manifest.enum",
    "smarter.apps.proxy.manifest.models.enum",
    "smarter.apps.secret.manifest.enum",
    "smarter.apps.vectorstore.manifest.enum",
]

PLAIN_MODULES = [
    "smarter.apps.connection.api.v1.views",
    "smarter.apps.connection.tasks",
    "smarter.apps.guardrail.exceptions",
    "smarter.apps.llmclient.urls",
    "smarter.apps.llmhost.enum",
    "smarter.apps.account.manifest.models.user_profile",
    "smarter.apps.secret.manifest.models.user_profile",
    "smarter.apps.provider.tests.utils",
]


class TestModuleImports(SmarterTestBase):
    """Test modules that are not otherwise imported."""

    def test_api_urlconfs(self):
        """Every app api urlconf redirects its root to v1/ and includes the v1 urls."""
        for module_name in API_URLCONFS:
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                self.assertEqual(module.app_name, "api")
                self.assertEqual(len(module.urlpatterns), 2)
                redirect, include = module.urlpatterns
                self.assertIsInstance(redirect, URLPattern)
                self.assertEqual(redirect.callback.view_initkwargs["url"], "v1/")
                self.assertIsInstance(include, URLResolver)
                self.assertEqual(str(include.pattern).rstrip("/"), "v1")

    def test_enum_modules(self):
        """Every enum class in these modules maps upper case names to string values."""
        enum_bases = (CommonSmarterEnumAbstract, ManifestSmarterEnumAbstract)
        for module_name in ENUM_MODULES:
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                enum_classes = [
                    obj
                    for _, obj in inspect.getmembers(module, inspect.isclass)
                    if issubclass(obj, enum_bases) and obj not in enum_bases and obj.__module__ == module_name
                ]
                self.assertTrue(enum_classes)
                for enum_class in enum_classes:
                    members = list(enum_class)
                    self.assertTrue(members, f"{enum_class.__name__} has no members")
                    for member in members:
                        self.assertTrue(member.name.isupper())
                        self.assertIsInstance(member.value, str)

    def test_connection_enum_values(self):
        from smarter.apps.connection.manifest.enum import (
            SAMApiConnectionSpecConnectionKeys,
            SAMSqlConnectionSpecConnectionKeys,
        )

        self.assertEqual(SAMApiConnectionSpecConnectionKeys.BASE_URL.value, "baseUrl")
        self.assertEqual(SAMSqlConnectionSpecConnectionKeys.DB_ENGINE.value, "dbEngine")

    def test_plain_modules(self):
        for module_name in PLAIN_MODULES:
            with self.subTest(module=module_name):
                self.assertIsNotNone(importlib.import_module(module_name))

    def test_llmhost_enum_reexports(self):
        """Smarter.apps.llmhost.enum re-exports the manifest enums."""
        from smarter.apps.llmhost import enum
        from smarter.apps.llmhost.manifest import enum as manifest_enum

        for name in enum.__all__:
            self.assertIs(getattr(enum, name), getattr(manifest_enum, name))

    def test_guardrail_exception(self):
        from smarter.apps.guardrail.exceptions import SmarterGuardrailException
        from smarter.common.exceptions import SmarterException

        self.assertTrue(issubclass(SmarterGuardrailException, SmarterException))
