"""Test :mod:`smarter.common.enum`."""

from smarter.common.enum import (
    SmarterEnum,
    SmarterEnumAbstract,
    SmarterResourceOwnershipFilterEnum,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class Kinds(SmarterEnumAbstract):
    """A test enumeration of manifest kinds."""

    ACCOUNT = "Account"
    PLUGIN = "Plugin"


class Colors(SmarterEnum):
    """A test SmarterEnum."""

    RED = "red"
    BLUE = "blue"
    lowercase = "ignored"
    NUMBER = 1


class TestSmarterEnumAbstract(SmarterTestBase):
    """Test SmarterEnumAbstract's class methods."""

    def test_all(self):
        self.assertEqual(Kinds.all(), ["Account", "Plugin"])
        self.assertEqual(Kinds.list_all(), "Account, Plugin")
        self.assertEqual(str(Kinds.ACCOUNT), "Account")

    def test_slugs(self):
        self.assertEqual(Kinds.singular_slugs(), ["account", "plugin"])
        self.assertEqual(Kinds.plural_slugs(), ["accounts", "plugins"])
        self.assertEqual(Kinds.all_slugs(), ["account", "plugin", "accounts", "plugins"])

    def test_from_url(self):
        self.assertEqual(Kinds.from_url("http://localhost:9357/api/v1/cli/describe/Account/"), "account")
        self.assertEqual(Kinds.from_url(b"http://localhost:9357/api/v1/cli/get/plugins/"), "plugins")

    def test_from_url_without_kind(self):
        """Test that a url that isn't the api, or a command without a kind, has no kind."""
        for url in (
            "http://localhost:9357/dashboard/account/",
            "http://localhost:9357/api/v1/cli/whoami/",
            "http://localhost:9357/api/v1/cli/status/",
            "http://localhost:9357/api/v1/cli/version/",
            "http://localhost:9357/api/v1/cli/get/notakind/",
        ):
            with self.subTest(url=url):
                self.assertIsNone(Kinds.from_url(url))


class TestSmarterEnum(SmarterTestBase):
    """Test SmarterEnum, whose values are its upper-case string attributes."""

    def test_all(self):
        self.assertEqual(Colors.all(), ["red", "blue"])
        self.assertEqual(Colors.list_all(), "red, blue")

    def test_str(self):
        self.assertIn("Colors", str(Colors()))
        color = Colors()
        color.value = "red"  # pylint: disable=attribute-defined-outside-init
        self.assertEqual(str(color), "red")

    def test_ownership_filter(self):
        self.assertEqual(
            {
                SmarterResourceOwnershipFilterEnum.OWNED,
                SmarterResourceOwnershipFilterEnum.SHARED,
                SmarterResourceOwnershipFilterEnum.ALL,
            },
            {"owned", "shared", "all"},
        )
