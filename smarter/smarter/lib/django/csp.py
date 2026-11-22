"""
The endpoint that browsers send Content Security Policy violation reports to.

Django's ``ContentSecurityPolicyMiddleware`` sends the policy (``SECURE_CSP_REPORT_ONLY``), whose
``report-uri`` is :data:`CSP_REPORT_PATH` on the platform's host. Each browser that sees a violation
posts a report there, in one of two shapes: ``application/csp-report``, one ``{"csp-report": {...}}``
object with kebab-case keys, or ``application/reports+json``, a list of Reporting API reports whose
``body`` has camelCase keys. :class:`CspViolation` reads both.

:class:`CspReportView` logs each distinct violation once an hour, at WARNING, so that a policy that is
about to be enforced can be checked in the pods' logs. The endpoint is public, so it bounds its work:
it reads at most :data:`MAX_REPORT_BYTES` and :data:`MAX_REPORTS_PER_REQUEST` reports, and logs a
violation it has already logged within the hour only once.

A report can carry secrets and personal data: a password reset link's token in the page's url, a
signed url in the blocked one, the text a person typed in the script sample. So the log names the page
by its url's name, the blocked resource by its origin, and the script by its path, and never logs the
sample, the referrer, the policy or the sender's address.
"""

import hashlib
import json
from typing import Optional
from urllib.parse import urlsplit

from cache_results import lazy_cache
from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.urls import Resolver404, resolve
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError

from smarter.lib import logging

logger = logging.getSmarterLogger(__name__)

CSP_REPORT_PATH = "/csp-report/"
"""The path of the report endpoint, which the policy's ``report-uri`` names on the platform's host."""

MAX_REPORT_BYTES = 64 * 1024
"""The largest request body that the endpoint reads.

A browser's report is a few kilobytes.
"""

MAX_REPORTS_PER_REQUEST = 20
"""How many reports of one ``application/reports+json`` request the endpoint reads."""

DEDUPLICATION_SECONDS = 60 * 60
"""How long the endpoint remembers a violation it has logged, so that it logs it only once."""

CACHE_KEY_PREFIX = "smarter.lib.django.csp.violation."

MAX_VALUE_LENGTH = 200
"""The longest value the log shows, after it has been reduced to an origin, a path or a name."""


class CspViolation(BaseModel):
    """
    One violation, from either report shape.

    Browsers send more fields than these. They are ignored on purpose: ``script-sample`` and
    ``sample`` hold the text of the page, ``referrer`` a url, ``original-policy`` the whole policy.
    """

    model_config = ConfigDict(extra="ignore")

    document_uri: str = Field("", validation_alias=AliasChoices("document-uri", "documentURL"))
    blocked_uri: str = Field("", validation_alias=AliasChoices("blocked-uri", "blockedURL"))
    effective_directive: str = Field(
        "", validation_alias=AliasChoices("effective-directive", "effectiveDirective", "violated-directive")
    )
    source_file: str = Field("", validation_alias=AliasChoices("source-file", "sourceFile"))
    line_number: Optional[int] = Field(None, validation_alias=AliasChoices("line-number", "lineNumber"))
    disposition: str = ""


def truncated(value: str) -> str:
    """
    Return ``value``, cut to :data:`MAX_VALUE_LENGTH` characters.

    :param value: A value for the log.
    :returns: The value, or its start followed by ``...``.
    """
    if len(value) <= MAX_VALUE_LENGTH:
        return value
    start = value[:MAX_VALUE_LENGTH]
    return f"{start}..."


def blocked_origin(blocked_uri: str) -> str:
    """
    Return what was blocked, without the path or query of its url.

    :param blocked_uri: The report's blocked uri: a url, or a keyword such as ``inline`` or ``eval``.
    :returns: The url's ``scheme://host``, its scheme alone for a url without a host
        (``data``, ``blob``), or the keyword.
    """
    parts = urlsplit(blocked_uri)
    if parts.netloc:
        origin = f"{parts.scheme}://{parts.netloc}"
        return truncated(origin)
    if parts.scheme:
        return parts.scheme
    return truncated(blocked_uri)


def source_path(source_file: str) -> str:
    """
    Return the script that caused the violation, without its query or fragment.

    :param source_file: The report's source file, a url.
    :returns: Its ``scheme://host/path``, or an empty string.
    """
    parts = urlsplit(source_file)
    if not parts.netloc:
        return ""
    path = f"{parts.scheme}://{parts.netloc}{parts.path}"
    return truncated(path)


def document_name(document_uri: str) -> str:
    """
    Return the page on which the violation happened, by the name of its url.

    A page's path can hold a secret, e.g. a password reset link's token, so it isn't logged.

    :param document_uri: The report's document uri, a url.
    :returns: ``host`` and the url's name, e.g. ``platform.example.com login_view``, or ``host``
        alone when the platform's urlconf doesn't know the path.
    """
    parts = urlsplit(document_uri)
    host = truncated(parts.netloc)
    try:
        match = resolve(parts.path or "/", urlconf=settings.ROOT_URLCONF)
    except Resolver404:
        return host
    return f"{host} {match.view_name}"


def raw_violations_in(data: object) -> list[object]:
    """
    Return the violation objects of a parsed report body, before they are validated.

    :param data: The parsed body: a ``{"csp-report": {...}}`` object, or a list of Reporting API reports.
    :returns: The ``csp-report`` object, or the ``body`` of each ``csp-violation`` report, at most
        :data:`MAX_REPORTS_PER_REQUEST`; an empty list for anything else.
    """
    retval: list[object] = []
    if isinstance(data, dict):
        retval.append(data.get("csp-report"))
        return retval
    if not isinstance(data, list):
        return retval
    for report in data[:MAX_REPORTS_PER_REQUEST]:
        if not isinstance(report, dict):
            continue
        if report.get("type") != "csp-violation":
            continue
        retval.append(report.get("body"))
    return retval


def violations_in(body: bytes) -> list[CspViolation]:
    """
    Return the violations in a report request's body, in either shape.

    :param body: The request's body.
    :returns: The violations, at most :data:`MAX_REPORTS_PER_REQUEST`, or an empty list for a body
        that isn't a report.
    """
    try:
        data = json.loads(body)
    except ValueError:
        return []

    raw_violations = raw_violations_in(data)
    retval = []
    for raw in raw_violations:
        if not isinstance(raw, dict):
            continue
        try:
            violation = CspViolation.model_validate(raw)
        except ValidationError:
            continue
        retval.append(violation)
    return retval


def log_violation(violation: CspViolation) -> bool:
    """
    Log a violation at WARNING, unless it was logged within :data:`DEDUPLICATION_SECONDS`.

    :param violation: The violation.
    :returns: True if it was logged.
    """
    directive = truncated(violation.effective_directive)
    blocked = blocked_origin(violation.blocked_uri)
    page = document_name(violation.document_uri)
    source = source_path(violation.source_file)
    line_number = violation.line_number

    identity = "|".join([directive, blocked, page, source, str(line_number)])
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    cache_key = f"{CACHE_KEY_PREFIX}{digest}"
    is_new = lazy_cache.add(cache_key, True, timeout=DEDUPLICATION_SECONDS)
    if not is_new:
        return False

    location = source or "the page"
    # a violation without a line number, e.g. a manifest's, is reported without one.
    if line_number is not None:
        location = f"{location} line {line_number}"
    logger.warning(
        "Content Security Policy (%s) violation: %s blocked %s on %s, from %s.",
        truncated(violation.disposition) or "unknown",
        directive,
        blocked,
        page,
        location,
    )
    return True


@method_decorator(csrf_exempt, name="dispatch")
class CspReportView(View):
    """
    Receive the browsers' Content Security Policy violation reports, and log them.

    It answers 204 to any report, read or not, so that a sender learns nothing, and 413 to a body
    over :data:`MAX_REPORT_BYTES`.
    """

    http_method_names = ["post"]

    def post(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        Log the violations in the request's body.

        :param request: The browser's report request.
        :returns: 204, or 413 for a body that is too large.
        """
        content_length = request.META.get("CONTENT_LENGTH") or "0"
        if not content_length.isdigit():
            return HttpResponse(status=400)
        if int(content_length) > MAX_REPORT_BYTES:
            return HttpResponse(status=413)
        violations = violations_in(request.body)
        for violation in violations:
            log_violation(violation)
        return HttpResponse(status=204)
