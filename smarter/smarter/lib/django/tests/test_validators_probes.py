"""
Test every method of :class:`smarter.lib.django.validators.SmarterValidator` with a set of probe values.

Each validate_*() method returns a value or raises a SmarterValueError, and each
is_*() method returns a bool, for any string. The targeted tests below check
the results of the branches that the probes reach.
"""

import inspect
import warnings

from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.unittest.base_classes import SmarterTestBase

STRING_PROBES = [
    "",
    " ",
    "a",
    "A",
    "1abc",
    "camelCase",
    "camelCase1",
    "PascalCase",
    "Pascal1",
    "PascalCase1",
    "snake_case",
    "UPPER",
    "has space",
    "{}",
    '{"a": 1}',
    "not json",
    "1.2.3",
    "1.2",
    "8080",
    "99999",
    "-1",
    "port",
    "/",
    "/api/v1/cli/",
    "/no-trailing-slash",
    "no-leading-slash/",
    "/bad path/",
    "example.com",
    "example.com:8080",
    "example.com:99999",
    ".example.com",
    ".",
    "*.example.com",
    "*.",
    "example.com.",
    "-bad-.com",
    "a" * 300,
    "localhost",
    "localhost:9357",
    "http://example.com",
    "https://example.com/path/",
    "https://api.example.com/",
    "ftp://example.com",
    "http://",
    "http://exa mple.com",
    "http://127.0.0.1:8000/",
    "127.0.0.1",
    "::1",
    "999.1.1.1",
    "user@example.com",
    "not-an-email",
    "1234-5678-9012",
    "123e4567-e89b-12d3-a456-426614174000",
    "X-Api-Key",
    "bad\nheader",
    "value\r\n",
    "a-slug",
    "Bad Slug!",
    "user.name-1",
]

LIST_PROBES = [[], ["example.com"], ["not valid!"], "not a list"]


def public_methods() -> dict:
    return {
        name: getattr(SmarterValidator, name)
        for name, member in inspect.getmembers(SmarterValidator)
        if not name.startswith("_")
        and callable(member)
        and isinstance(inspect.getattr_static(SmarterValidator, name), staticmethod)
    }


class TestSmarterValidatorProbes(SmarterTestBase):
    """Test that every method validates or refuses each probe without an unexpected exception."""

    def test_probes(self):
        for name, method in public_methods().items():
            probes = LIST_PROBES if name.startswith("validate_list_of") else STRING_PROBES
            for value in probes:
                with self.subTest(method=name, value=value):
                    try:
                        with warnings.catch_warnings():
                            warnings.simplefilter("ignore", DeprecationWarning)
                            result = method(value)
                    except (SmarterValueError, TypeError, AttributeError):
                        # TypeError and AttributeError are raised for a probe of the wrong type, e.g. a list.
                        continue
                    if name.startswith("is_"):
                        self.assertIsInstance(result, bool)


class TestSmarterValidatorBranches(SmarterTestBase):
    """Test the results of the validators' branches."""

    def test_case(self):
        self.assertEqual(SmarterValidator.validate_camel_case("camelCase"), "camelCase")
        self.assertTrue(SmarterValidator.is_valid_camel_case("camelCase"))
        self.assertFalse(SmarterValidator.is_valid_camel_case("PascalCase"))
        self.assertTrue(SmarterValidator.is_valid_pascal_case("Pascal"))
        self.assertFalse(SmarterValidator.is_valid_pascal_case("camelCase"))
        self.assertTrue(SmarterValidator.is_valid_snake_case("snake_case"))
        self.assertFalse(SmarterValidator.is_valid_snake_case("camelCase"))

    def test_json(self):
        self.assertIsNone(SmarterValidator.validate_json("  "))
        self.assertTrue(SmarterValidator.is_valid_json('{"a": 1}'))
        self.assertFalse(SmarterValidator.is_valid_json("not json"))
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_json(1)  # type: ignore[arg-type]

    def test_port(self):
        self.assertEqual(SmarterValidator.validate_port("8080"), "8080")
        self.assertFalse(SmarterValidator.is_valid_port("99999"))
        self.assertFalse(SmarterValidator.is_valid_port("port"))

    def test_url_path(self):
        self.assertTrue(SmarterValidator.is_valid_url_path("/api/v1/"))
        self.assertFalse(SmarterValidator.is_valid_url_path("api/v1/"))
        self.assertFalse(SmarterValidator.is_valid_url_path("/bad path/"))

    def test_url(self):
        self.assertTrue(SmarterValidator.is_valid_url("https://example.com/path/"))
        self.assertTrue(SmarterValidator.is_valid_url("http://localhost:9357/"))
        self.assertFalse(SmarterValidator.is_valid_url("ftp://example.com"))
        self.assertFalse(SmarterValidator.is_valid_url(""))
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_url(1)  # type: ignore[arg-type]

    def test_hostname(self):
        self.assertEqual(SmarterValidator.validate_hostname("example.com"), "example.com")
        self.assertTrue(SmarterValidator.is_valid_hostname(".example.com"))
        self.assertTrue(SmarterValidator.is_valid_hostname("*.example.com"))
        self.assertTrue(SmarterValidator.is_valid_hostname("example.com:8080"))
        for hostname in (".", "*.", "example.com:99999", "a" * 300, "-bad-.com", "::1", "http://127.0.0.1:8000/"):
            with self.subTest(hostname=hostname):
                self.assertFalse(SmarterValidator.is_valid_hostname(hostname))

    def test_domain(self):
        self.assertEqual(SmarterValidator.validate_domain("example.com"), "example.com")
        self.assertIsNone(SmarterValidator.validate_domain(None))
        self.assertEqual(SmarterValidator.validate_domain("localhost"), "localhost")
        self.assertFalse(SmarterValidator.is_valid_domain("not valid!"))

    def test_url_endpoint(self):
        self.assertTrue(SmarterValidator.is_valid_url_endpoint("/api/v1/"))
        for url in ("api/v1/", "/api/v1", "/bad path/"):
            with self.subTest(url=url):
                with self.assertRaises(SmarterValueError):
                    SmarterValidator.validate_url_endpoint(url)

    def test_is_api_endpoint(self):
        self.assertTrue(SmarterValidator.is_api_endpoint("/api/v1/cli/"))
        self.assertTrue(SmarterValidator.is_api_endpoint("https://alpha.api.example.com/v1/"))
        self.assertFalse(SmarterValidator.is_api_endpoint("https://example.com/dashboard/"))
        self.assertFalse(SmarterValidator.is_api_endpoint(None))  # type: ignore[arg-type]
        self.assertFalse(SmarterValidator.is_api_endpoint("not a url"))

    def test_lists(self):
        SmarterValidator.validate_list_of_domains(["example.com"])
        SmarterValidator.validate_list_of_emails(["a@example.com"])
        SmarterValidator.validate_list_of_ips(["127.0.0.1"])
        SmarterValidator.validate_list_of_ports(["80"])
        SmarterValidator.validate_list_of_urls(["https://example.com"])
        SmarterValidator.validate_list_of_uuids(["123e4567-e89b-12d3-a456-426614174000"])
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_list_of_emails(["not-an-email"])

    def test_url_helpers(self):
        self.assertEqual(SmarterValidator.base_url("https://example.com/path/"), "https://example.com/")
        self.assertEqual(SmarterValidator.base_domain("https://example.com/path/"), "example.com")
        self.assertIsNone(SmarterValidator.base_url(""))
        self.assertIsNone(SmarterValidator.base_domain(""))
        self.assertEqual(SmarterValidator.trailing_slash("https://example.com"), "https://example.com/")
        self.assertIsNone(SmarterValidator.trailing_slash(""))
        self.assertEqual(SmarterValidator.leading_slash("api/"), "/api/")
        self.assertEqual(SmarterValidator.leading_slash("/api/"), "/api/")
        self.assertIsNone(SmarterValidator.leading_slash(""))

    def test_urlify(self):
        self.assertEqual(SmarterValidator.urlify("example.com"), "http://example.com/")
        self.assertEqual(SmarterValidator.urlify("example.com", environment="prod"), "https://example.com/")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.urlify("")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            with self.assertRaises(SmarterValueError):
                SmarterValidator.urlify("example.com", scheme="ftp")

    def test_misc(self):
        with self.assertRaises(SmarterValueError):
            SmarterValidator.raise_error("an error")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_no_spaces("has space")
        SmarterValidator.validate_no_spaces("nospace")
        self.assertTrue(SmarterValidator.is_valid_username("user.name-1"))
        self.assertFalse(SmarterValidator.is_valid_username("bad user"))
        self.assertTrue(SmarterValidator.is_valid_llmclient_slug("a-slug"))
        self.assertFalse(SmarterValidator.is_valid_llmclient_slug("Bad Slug!"))
