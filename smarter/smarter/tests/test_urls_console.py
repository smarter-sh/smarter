"""
Test the SAM resource apps' url tables in :mod:`smarter.urls.console`, :mod:`smarter.apps.api.v1.urls` and.

:mod:`smarter.apps.api.web.urls`.

Each SAM app's urls are mounted only if its ``smarter_settings.enable_<app>`` flag is true. The urlconfs are
built once, at import, with the default settings, in which every flag is true. The helper that reads the
flags is tested in :mod:`smarter.lib.manifest.tests.test_sam_apps`.
"""

from typing import Optional, Union

from django.urls import get_resolver

from smarter.apps.api.v1.urls import SAM_APP_API_URLS
from smarter.apps.api.web.urls import SAM_APP_WEB_API_URLS
from smarter.common.conf.settings import Settings
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib.manifest.sam_apps import SAM_APPS, SamAppUrls
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.urls.console import SAM_APP_CONSOLE_URLS

TABLES: dict[str, list[SamAppUrls]] = {
    "console": SAM_APP_CONSOLE_URLS,
    "api_v1": SAM_APP_API_URLS,
    "api_web": SAM_APP_WEB_API_URLS,
}


class TestSamAppUrlTables(SmarterTestBase):
    """Test that each urlconf's table covers every SAM app, and that its urls are mounted."""

    def test_every_app_is_in_every_table(self):
        """Test that every SAM app has urls in each table, and that each table names only SAM apps' flags."""
        app_settings = [sam_app.setting for sam_app in SAM_APPS]
        for table_name, table in TABLES.items():
            table_settings = [app_urls.setting for app_urls in table]
            with self.subTest(table=table_name):
                for setting in app_settings:
                    self.assertIn(setting, table_settings)
                for setting in table_settings:
                    self.assertIn(setting, app_settings)

    def test_console_urlconf_mounts_every_app(self):
        """Test that the console's urlconf has every app's namespace, with the default settings."""
        resolver = get_resolver("smarter.urls.console")
        for app_urls in SAM_APP_CONSOLE_URLS:
            with self.subTest(namespace=app_urls.namespace):
                self.assertIn(app_urls.namespace, resolver.namespace_dict)


class TestParseEnableSamApp(SmarterTestBase):
    """Test the validator of the SAM apps' feature flags."""

    def test_values(self):
        """Test that the flags parse booleans and strings, and that an empty value is the default."""
        cases: list[tuple[Optional[Union[bool, str]], bool]] = [
            (False, False),
            ("false", False),
            ("no", False),
            (True, True),
            ("yes", True),
            ("", True),
            (None, True),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                settings = Settings.model_validate({"app_secret_enable": value})
                self.assertIs(settings.app_secret_enable, expected)

    def test_invalid(self):
        """Test that a value that is neither a boolean nor a string is a configuration error."""
        with self.assertRaises(SmarterConfigurationError):
            Settings.model_validate({"app_proxy_enable": 3.5})
