"""Test the SmarterValidator class."""

from smarter.common.exceptions import SmarterValueError
from smarter.lib.unittest.base_classes import SmarterTestBase

from ..validators import SmarterValidator


class TestSmarterValidator(SmarterTestBase):
    """Test the SmarterValidator class."""

    def test_validate_camel_case(self):
        SmarterValidator.validate_camel_case("camelCase")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_camel_case("CamelCase")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_camel_case("camel_case")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_camel_case("")

    def test_is_valid_camel_case(self):
        self.assertTrue(SmarterValidator.is_valid_camel_case("camelCase"))
        self.assertFalse(SmarterValidator.is_valid_camel_case("CamelCase"))

    def test_validate_snake_case(self):
        SmarterValidator.validate_snake_case("snake_case")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_snake_case("SnakeCase")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_snake_case("snake-case")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_snake_case("")

    def test_is_valid_snake_case(self):
        self.assertTrue(SmarterValidator.is_valid_snake_case("snake_case"))
        self.assertFalse(SmarterValidator.is_valid_snake_case("SnakeCase"))

    def test_validate_pascal_case(self):
        SmarterValidator.validate_pascal_case("Pascalcase")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_pascal_case("pascalCase")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_pascal_case("Pascal_Case")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_pascal_case("")

    def test_is_valid_pascal_case(self):
        self.assertTrue(SmarterValidator.is_valid_pascal_case("Pascalcase"))
        self.assertFalse(SmarterValidator.is_valid_pascal_case("pascalCase"))

    def test_validate_json(self):
        SmarterValidator.validate_json('{"key": "value"}')
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_json("{key: value}")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_json(123)

    def test_is_valid_json(self):
        self.assertTrue(SmarterValidator.is_valid_json('{"key": "value"}'))
        self.assertFalse(SmarterValidator.is_valid_json("{key: value}"))

    def test_validate_semantic_version(self):
        SmarterValidator.validate_semantic_version("1.0.0")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_semantic_version("1.0")

    def test_is_valid_semantic_version(self):
        self.assertTrue(SmarterValidator.is_valid_semantic_version("1.0.0"))
        self.assertFalse(SmarterValidator.is_valid_semantic_version("1.0"))

    def test_validate_is_not_none(self):
        SmarterValidator.validate_is_not_none("not none")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_is_not_none(None)
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_is_not_none("")

    def test_is_not_none(self):
        self.assertTrue(SmarterValidator.is_not_none("not none"))
        self.assertFalse(SmarterValidator.is_not_none(None))

    def test_validate_session_key(self):
        valid = "a" * 64
        SmarterValidator.validate_session_key(valid)
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_session_key("short")

    def test_validate_account_number(self):
        SmarterValidator.validate_account_number("1234-5678-9012")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_account_number("123456789012")

    def test_validate_domain(self):
        SmarterValidator.validate_domain("localhost")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_domain("///invalid_domain=?")

    def test_validate_email(self):
        SmarterValidator.validate_email("test@example.com")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_email("not-an-email")

    def test_validate_ip(self):
        SmarterValidator.validate_ip("127.0.0.1")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_ip("999.999.999.999")

    def test_validate_port(self):
        SmarterValidator.validate_port("8080")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_port("99999")

    def test_validate_url(self):
        SmarterValidator.validate_url("http://localhost/")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_url("notaurl")

    def test_validate_hostname(self):
        SmarterValidator.validate_hostname("localhost")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_hostname("invalid_hostname!")

    def test_validate_uuid(self):
        SmarterValidator.validate_uuid("123e4567-e89b-12d3-a456-426614174000")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_uuid("not-a-uuid")

    def test_validate_clean_string(self):
        SmarterValidator.validate_clean_string("clean-string")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_clean_string("bad string!")

    def test_validate_http_request_header_key(self):
        SmarterValidator.validate_http_request_header_key("X-Test-Header")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_http_request_header_key("X Test Header")

    def test_validate_http_request_header_value(self):
        SmarterValidator.validate_http_request_header_value("value123")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_http_request_header_value("value\n123")

    def test_is_valid_http_request_header_key(self):
        self.assertTrue(SmarterValidator.is_valid_http_request_header_key("X-Test-Header"))
        self.assertFalse(SmarterValidator.is_valid_http_request_header_key("X Test Header"))

    def test_is_valid_http_request_header_value(self):
        self.assertTrue(SmarterValidator.is_valid_http_request_header_value("value123"))
        self.assertFalse(SmarterValidator.is_valid_http_request_header_value("value\n123"))

    def test_is_valid_session_key(self):
        self.assertTrue(SmarterValidator.is_valid_session_key("a" * 64))
        self.assertFalse(SmarterValidator.is_valid_session_key("short"))

    def test_is_valid_account_number(self):
        self.assertTrue(SmarterValidator.is_valid_account_number("1234-5678-9012"))
        self.assertFalse(SmarterValidator.is_valid_account_number("123456789012"))

    def test_is_valid_domain(self):
        self.assertTrue(SmarterValidator.is_valid_domain("localhost"))
        self.assertFalse(SmarterValidator.is_valid_domain("&&$invalid_domain)()"))

    def test_is_valid_email(self):
        self.assertTrue(SmarterValidator.is_valid_email("test@example.com"))
        self.assertFalse(SmarterValidator.is_valid_email("not-an-email"))

    def test_is_valid_ip(self):
        self.assertTrue(SmarterValidator.is_valid_ip("127.0.0.1"))
        self.assertFalse(SmarterValidator.is_valid_ip("999.999.999.999"))

    def test_is_valid_port(self):
        self.assertTrue(SmarterValidator.is_valid_port("8080"))
        self.assertFalse(SmarterValidator.is_valid_port("99999"))

    def test_is_valid_url(self):
        self.assertTrue(SmarterValidator.is_valid_url("http://localhost/"))
        self.assertFalse(SmarterValidator.is_valid_url("notaurl"))

    def test_is_valid_hostname(self):
        self.assertTrue(SmarterValidator.is_valid_hostname("localhost"))
        self.assertFalse(SmarterValidator.is_valid_hostname("invalid_hostname!"))

    def test_is_valid_uuid(self):
        self.assertTrue(SmarterValidator.is_valid_uuid("123e4567-e89b-12d3-a456-426614174000"))
        self.assertFalse(SmarterValidator.is_valid_uuid("not-a-uuid"))

    def test_is_valid_cleanstring(self):
        self.assertTrue(SmarterValidator.is_valid_cleanstring("clean-string"))
        self.assertFalse(SmarterValidator.is_valid_cleanstring("bad string!"))

    def test_is_valid_url_endpoint(self):
        self.assertTrue(SmarterValidator.is_valid_url_endpoint("/api/v1/tests/unauthenticated/list/"))
        self.assertFalse(SmarterValidator.is_valid_url_endpoint("api/v1/tests/unauthenticated/list"))

    def test_validate_url_endpoint(self):
        SmarterValidator.validate_url_endpoint("/api/v1/tests/unauthenticated/list/")
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_url_endpoint("api/v1/tests/unauthenticated/list")

    def test_validate_list_of_account_numbers(self):
        SmarterValidator.validate_list_of_account_numbers(["1234-5678-9012"])
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_list_of_account_numbers(["bad"])

    def test_validate_list_of_domains(self):
        SmarterValidator.validate_list_of_domains(["localhost"])
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_list_of_domains(["$bad_domain()"])

    def test_validate_list_of_emails(self):
        SmarterValidator.validate_list_of_emails(["test@example.com"])
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_list_of_emails(["not-an-email"])

    def test_validate_list_of_ips(self):
        SmarterValidator.validate_list_of_ips(["127.0.0.1"])
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_list_of_ips(["999.999.999.999"])

    def test_validate_list_of_ports(self):
        SmarterValidator.validate_list_of_ports(["8080"])
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_list_of_ports(["99999"])

    def test_validate_list_of_urls(self):
        SmarterValidator.validate_list_of_urls(["http://localhost/"])
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_list_of_urls(["notaurl"])

    def test_validate_list_of_uuids(self):
        SmarterValidator.validate_list_of_uuids(["123e4567-e89b-12d3-a456-426614174000"])
        with self.assertRaises(SmarterValueError):
            SmarterValidator.validate_list_of_uuids(["not-a-uuid"])

    def test_base_domain(self):
        self.assertEqual(SmarterValidator.base_domain("http://example.com/foo/"), "example.com")

    def test_base_url(self):
        self.assertEqual(SmarterValidator.base_url("http://example.com/foo/"), "http://example.com/")

    def test_trailing_slash(self):
        self.assertEqual(SmarterValidator.trailing_slash("http://example.com"), "http://example.com/")
        self.assertEqual(SmarterValidator.trailing_slash("http://example.com/"), "http://example.com/")

    def test_urlify(self):
        self.assertTrue(SmarterValidator.urlify("example.com").startswith("http://"))
        self.assertTrue(SmarterValidator.urlify("example.com").endswith("/"))
        with self.assertRaises(SmarterValueError):
            SmarterValidator.urlify("example.com", scheme="ftp")

    def test_raise_error(self):
        with self.assertRaises(SmarterValueError):
            SmarterValidator.raise_error("fail")
