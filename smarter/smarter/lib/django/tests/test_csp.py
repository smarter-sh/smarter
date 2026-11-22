"""Test the Content Security Policy report endpoint: :mod:`smarter.lib.django.csp`."""

import json
from http import HTTPStatus
from unittest.mock import patch

from django.conf import settings
from django.test import Client

from smarter.lib.django.csp import (
    CSP_REPORT_PATH,
    MAX_REPORT_BYTES,
    MAX_REPORTS_PER_REQUEST,
    MAX_VALUE_LENGTH,
    CspViolation,
    blocked_origin,
    document_name,
    log_violation,
    source_path,
    truncated,
    violations_in,
)
from smarter.lib.django.shortcuts import reverse
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.urls.console import ConsoleReverseNames

MODULE = "smarter.lib.django.csp"

RESET_LINK = "http://localhost:9357/password-reset-link/MTk1NA/secret-token-123/?next=/x"

# a report as Chrome sends it to report-uri (application/csp-report).
CSP_REPORT = {
    "csp-report": {
        "document-uri": RESET_LINK,
        "referrer": "https://referrer.example.com/private?token=abc",
        "violated-directive": "script-src-elem",
        "effective-directive": "script-src-elem",
        "original-policy": "default-src 'self'",
        "disposition": "report",
        "blocked-uri": "https://cdn.example.com/lib.js?signature=s3cr3t",
        "line-number": 12,
        "source-file": "https://cdn.example.com/static/app.js?v=2",
        "script-sample": "a person's private text",
        "status-code": 200,
    }
}

# the same report as the Reporting API sends it (application/reports+json).
REPORTING_API_REPORTS = [
    {
        "type": "csp-violation",
        "age": 10,
        "url": RESET_LINK,
        "body": {
            "documentURL": RESET_LINK,
            "blockedURL": "inline",
            "effectiveDirective": "style-src-attr",
            "disposition": "report",
            "sample": "a person's private text",
            "lineNumber": 3,
        },
    },
    {"type": "deprecation", "body": {"id": "something"}},
]


class TestCspReportHelpers(SmarterTestBase):
    """Each value of a report is reduced to what can be logged safely."""

    def test_blocked_origin(self):
        self.assertEqual(blocked_origin("https://cdn.example.com/lib.js?signature=s3cr3t"), "https://cdn.example.com")
        self.assertEqual(blocked_origin("data:image/png;base64,AAAA"), "data")
        self.assertEqual(blocked_origin("inline"), "inline")
        self.assertEqual(blocked_origin(""), "")

    def test_source_path(self):
        self.assertEqual(
            source_path("https://cdn.example.com/static/app.js?v=2#x"), "https://cdn.example.com/static/app.js"
        )
        self.assertEqual(source_path(""), "")

    def test_document_name_hides_the_path(self):
        """A password reset link's token is in its path: the log names the url instead."""
        name = document_name(RESET_LINK)
        self.assertEqual(name, "localhost:9357 password_reset_link")
        self.assertNotIn("secret-token", name)

    def test_document_name_of_an_unknown_path(self):
        self.assertEqual(document_name("https://chat.example.com/no/such/page/"), "chat.example.com")

    def test_truncated(self):
        self.assertEqual(truncated("short"), "short")
        long_value = "x" * (MAX_VALUE_LENGTH + 50)
        self.assertEqual(len(truncated(long_value)), MAX_VALUE_LENGTH + 3)

    def test_violations_in_a_csp_report(self):
        violations = violations_in(json.dumps(CSP_REPORT).encode())
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].effective_directive, "script-src-elem")
        self.assertEqual(violations[0].line_number, 12)

    def test_violations_in_reporting_api_reports(self):
        """Only csp-violation reports are read, and only up to the limit."""
        violations = violations_in(json.dumps(REPORTING_API_REPORTS).encode())
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].blocked_uri, "inline")
        many = [REPORTING_API_REPORTS[0]] * (MAX_REPORTS_PER_REQUEST + 5)
        self.assertEqual(len(violations_in(json.dumps(many).encode())), MAX_REPORTS_PER_REQUEST)

    def test_violations_in_something_else(self):
        for body in (b"not json", b"42", b'{"other": 1}', b'[1, {"type": "csp-violation", "body": "x"}]'):
            with self.subTest(body=body):
                self.assertEqual(violations_in(body), [])
        bad_line_number = {"csp-report": {"line-number": "not a number"}}
        self.assertEqual(violations_in(json.dumps(bad_line_number).encode()), [])

    def test_the_model_ignores_the_samples(self):
        violation = CspViolation.model_validate(CSP_REPORT["csp-report"])
        self.assertNotIn("private", violation.model_dump_json())


class TestCspReportLogging(SmarterTestBase):
    """A violation is logged once an hour, without its secrets."""

    def violation(self) -> CspViolation:
        raw = dict(CSP_REPORT["csp-report"])
        raw["line-number"] = 1000 + len(self.hash_suffix)
        raw["source-file"] = f"https://cdn.example.com/static/{self.hash_suffix}.js"
        return CspViolation.model_validate(raw)

    def test_log_violation_once(self):
        violation = self.violation()
        with patch(f"{MODULE}.logger") as logger:
            self.assertTrue(log_violation(violation))
            self.assertFalse(log_violation(violation))
        logger.warning.assert_called_once()
        logged = " ".join(str(value) for value in logger.warning.call_args.args)
        for secret in ("secret-token", "s3cr3t", "private", "referrer", "next="):
            with self.subTest(secret=secret):
                self.assertNotIn(secret, logged)
        self.assertIn("https://cdn.example.com", logged)
        self.assertIn("password_reset_link", logged)
        self.assertIn(f"line {violation.line_number}", logged)

    def test_log_violation_without_a_line_number(self):
        """A violation without a line number, e.g. a web app manifest's, doesn't log "line None"."""
        violation = self.violation().model_copy(update={"line_number": None})
        with patch(f"{MODULE}.logger") as logger:
            self.assertTrue(log_violation(violation))
        logged = " ".join(str(value) for value in logger.warning.call_args.args)
        self.assertNotIn("None", logged)


class TestWebAppManifest(SmarterTestBase):
    """The web app manifest is served from the page's own origin, which the policy's default-src allows."""

    def setUp(self):
        super().setUp()
        self.client = Client()

    def test_the_manifest_is_served_from_the_platforms_origin(self):
        path = reverse(ConsoleReverseNames.site_webmanifest)
        self.assertEqual(path, "/site.webmanifest")
        response = self.client.get(path)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "application/manifest+json")
        manifest = json.loads(b"".join(response.streaming_content))  # type: ignore[attr-defined]
        self.assertEqual(manifest["start_url"], "/")

    def test_the_templates_link_it_from_the_platforms_origin(self):
        """The base template links the same-origin manifest, never {% static %}'s, which may be the CDN's."""
        template = (settings.BASE_DIR / "templates" / "base.html").read_text(encoding="utf-8")
        self.assertIn("{% url 'site_webmanifest' %}", template)
        self.assertNotIn("{% static 'site.webmanifest' %}", template)

    def test_default_src_covers_the_manifest(self):
        """With no manifest-src, a browser checks the manifest against default-src, which is 'self'."""
        policy = settings.SECURE_CSP_REPORT_ONLY
        self.assertNotIn("manifest-src", policy)
        self.assertEqual(policy["default-src"], ["'self'"])


class TestCspReportView(SmarterTestBase):
    """Browsers post reports to the endpoint that the policy names."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.path = reverse(ConsoleReverseNames.csp_report)

    def test_the_policy_names_the_endpoint(self):
        self.assertEqual(self.path, CSP_REPORT_PATH)
        self.assertTrue(settings.CSP_REPORT_URL.endswith(CSP_REPORT_PATH))
        policy = self.client.get("/login/")["Content-Security-Policy-Report-Only"]
        self.assertIn(f"report-uri {settings.CSP_REPORT_URL}", policy)

    def test_a_report_is_logged(self):
        body = json.dumps(CSP_REPORT)
        with patch(f"{MODULE}.log_violation") as log:
            response = self.client.post(self.path, data=body, content_type="application/csp-report")
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        log.assert_called_once()

    def test_reporting_api_reports_are_logged(self):
        body = json.dumps(REPORTING_API_REPORTS)
        with patch(f"{MODULE}.log_violation") as log:
            response = self.client.post(self.path, data=body, content_type="application/reports+json")
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)
        log.assert_called_once()

    def test_no_csrf_token_is_needed(self):
        client = Client(enforce_csrf_checks=True)
        body = json.dumps(CSP_REPORT)
        with patch(f"{MODULE}.log_violation"):
            response = client.post(self.path, data=body, content_type="application/csp-report")
        self.assertEqual(response.status_code, HTTPStatus.NO_CONTENT)

    def test_a_large_body_is_refused(self):
        body = "x" * (MAX_REPORT_BYTES + 1)
        with patch(f"{MODULE}.log_violation") as log:
            response = self.client.post(self.path, data=body, content_type="application/csp-report")
        self.assertEqual(response.status_code, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        log.assert_not_called()

    def test_a_bad_content_length_is_refused(self):
        response = self.client.post(self.path, data="{}", content_type="application/csp-report", CONTENT_LENGTH="x")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_only_post(self):
        self.assertEqual(self.client.get(self.path).status_code, HTTPStatus.METHOD_NOT_ALLOWED)
