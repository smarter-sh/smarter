"""
Serializers for Django HTTP requests and user objects in the Smarter API.

This module defines custom serializers for:

- Serializing the `User` model for API responses.
- Representing anonymous and authenticated HTTP request data for use with the Django REST Framework.

These serializers enable structured, validated, and documented representations of HTTP request and user data for API endpoints and internal processing.
"""

import re
from typing import Optional

import yaml
from django.http import HttpRequest
from django.http.request import RawPostDataException
from pydantic import JsonValue, TypeAdapter, ValidationError
from rest_framework import serializers

from smarter.apps.account.models import User
from smarter.common.const import SmarterHttpMethods

MAX_SERIALIZED_BODY_SIZE = 1024 * 1024
"""The largest request body, in bytes, that a serialized request keeps.

A larger one is replaced by its size.
"""

REDACTED_VALUE = "********"
"""What a credential in a serialized request body is replaced with."""

SENSITIVE_BODY_KEYS = frozenset(
    {
        "access_key",
        "api_key",
        "apikey",
        "authorization",
        "client_secret",
        "credentials",
        "csrfmiddlewaretoken",
        "passwd",
        "password",
        "private_key",
        "secret",
        "secret_key",
        "session_key",
        "sessionid",
        "token",
    }
)
"""
The keys, in snake_case, whose values a serialized request body never keeps.

A key is also sensitive when it ends in ``_`` and one of these, e.g. ``proxyPassword`` or
``aws_secret_access_key``. Keys are matched whole, not as substrings, so that usage counters
such as ``max_tokens`` are kept.
"""

_CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")

JSON_VALUE: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)
"""Validates a parsed request body as JSON."""


def is_sensitive_body_key(key: str) -> bool:
    """
    Return whether a request body's key names a credential.

    :param key: The key, in snake_case, camelCase or kebab-case.
    :returns: True if the key, or its last ``_``-separated suffix, is in :data:`SENSITIVE_BODY_KEYS`.
    """
    normalized = _CAMEL_CASE_BOUNDARY.sub("_", key).lower().replace("-", "_")
    if normalized in SENSITIVE_BODY_KEYS:
        return True
    return any(normalized.endswith("_" + sensitive) for sensitive in SENSITIVE_BODY_KEYS)


def redact_body(value: JsonValue) -> JsonValue:
    """
    Return a copy of a parsed request body, with its credentials replaced by :data:`REDACTED_VALUE`.

    A value is replaced when its key is sensitive (see :func:`is_sensitive_body_key`), and a Secret
    manifest's ``spec.config.value`` is always replaced.

    :param value: The parsed body, or a part of it.
    :returns: The redacted copy.
    """
    if isinstance(value, list):
        return [redact_body(item) for item in value]
    if not isinstance(value, dict):
        return value
    redacted: dict[str, JsonValue] = {}
    for key, item in value.items():
        if item is not None and is_sensitive_body_key(key):
            redacted[key] = REDACTED_VALUE
        else:
            redacted[key] = redact_body(item)
    if redacted.get("kind") == "Secret":
        spec = redacted.get("spec")
        config = spec.get("config") if isinstance(spec, dict) else None
        if isinstance(config, dict) and "value" in config:
            config["value"] = REDACTED_VALUE
    return redacted


def read_body(request: HttpRequest) -> bytes:
    """
    Return a request's raw body.

    :param request: The request.
    :returns: The body, or empty bytes if it has none, or it was read as a stream, e.g. a file upload.
    """
    try:
        body = getattr(request, "body", None)
    except RawPostDataException:
        return b""
    if isinstance(body, (bytes, bytearray)):
        return bytes(body)
    return b""


def parse_body_text(text: str) -> JsonValue:
    """
    Parse a request body's text as JSON, or else as YAML, e.g. a manifest.

    :param text: The body's text.
    :returns: The parsed value, or the text itself if it is neither, or is YAML that isn't JSON,
        e.g. with a date or an integer key.
    """
    try:
        return JSON_VALUE.validate_json(text)
    except ValidationError:
        pass
    try:
        return JSON_VALUE.validate_python(yaml.safe_load(text))
    except (yaml.YAMLError, ValidationError):
        return text


def serialize_body(request: HttpRequest) -> JsonValue:
    """
    Return a request's body, parsed and redacted, for the journal.

    A JSON or YAML body is returned parsed, other text as it is, and a binary or larger than
    :data:`MAX_SERIALIZED_BODY_SIZE` body only as its size. Credentials are replaced by
    :func:`redact_body`; text that can't be parsed can't be redacted, and is kept only if it
    has no sensitive key in it.

    :param request: The request.
    :returns: The body, None if there is none or it can't be read, or ``{"size": n}``.
    """
    body = read_body(request)
    if not body:
        return None
    if len(body) > MAX_SERIALIZED_BODY_SIZE:
        return {"size": len(body)}
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return {"size": len(body)}
    parsed = parse_body_text(text)
    if isinstance(parsed, (dict, list)):
        return redact_body(parsed)
    if any(is_sensitive_body_key(word) for word in re.findall(r"[A-Za-z0-9_-]+", text)):
        return {"size": len(body)}
    return text


SAFE_META_KEYS = frozenset(
    {
        "CONTENT_LENGTH",
        "CONTENT_TYPE",
        "HTTP_ACCEPT",
        "HTTP_ACCEPT_LANGUAGE",
        "HTTP_HOST",
        "HTTP_ORIGIN",
        "HTTP_REFERER",
        "HTTP_USER_AGENT",
        "HTTP_X_FORWARDED_FOR",
        "PATH_INFO",
        "QUERY_STRING",
        "REMOTE_ADDR",
        "REQUEST_METHOD",
        "SERVER_NAME",
        "SERVER_PORT",
    }
)
"""
The ``request.META`` keys that a serialized request keeps.

Serialized requests are stored in the journal, so this is an allowlist: headers that
carry credentials (``HTTP_AUTHORIZATION``, ``HTTP_COOKIE``, ``HTTP_X_CSRFTOKEN``),
and the server's own environment, are never stored.
"""


class UserSerializer(serializers.ModelSerializer):
    """
    Serializes the ``User`` model for use in Django REST Framework APIs.

    This serializer provides a minimal representation of the ``User`` object, exposing only the ``username`` field.
    It is intended for use in API responses where user identification is required, but sensitive information
    should be excluded.

    :param str username: The unique username of the user.

    **Example**

    .. code-block:: python

        from smarter.lib.django.http.serializers import UserSerializer
        from smarter.apps.account.models import User

        user = User(username="alice")
        serializer = UserSerializer(user)
        print(serializer.data)
        # Output: {'username': 'alice'}

    .. note::
        This serializer is designed to be minimal for privacy and security. Only the ``username`` field is exposed.

    .. warning::
        Do not extend this serializer to include sensitive fields (such as passwords or email addresses) unless
        absolutely necessary and with proper security considerations.
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        model = User
        fields = [
            "username",
        ]


class HttpAnonymousRequestSerializer(serializers.Serializer):
    """
    Serializes anonymous HTTP request data for the Smarter API.

    This serializer is designed to represent the structure of an unauthenticated Django HTTP request,
    capturing key request attributes for use in API endpoints, logging, or debugging. It is intended
    for scenarios where user authentication is not required or available.

    :param str url: The absolute URL of the request (read-only, derived from the request object).
    :param str method: The HTTP method (e.g., ``GET``, ``POST``, ``PUT``, ``DELETE``).
    :param dict GET: Query parameters from the request URL.
    :param dict POST: Data submitted in the body of a POST request.
    :param dict META: The request's headers and metadata, limited to :data:`SAFE_META_KEYS`.
    :param body: The request's body, parsed and with its credentials redacted (see :func:`serialize_body`).
    :param str path: The path portion of the request URL.
    :param str encoding: The encoding used for the request body.
    :param str content_type: The MIME type of the request body.

    Cookies are never serialized, and ``META`` keeps only :data:`SAFE_META_KEYS`, because
    serialized requests are stored in the journal and must not hold API keys or session ids.

    **Example**

    .. code-block:: python

        from smarter.lib.django.http.serializers import HttpAnonymousRequestSerializer
        from django.http import HttpRequest

        request = HttpRequest()
        request.method = "GET"
        request.path = "/api/v1/resource/"
        request.GET = {"search": "test"}
        request.encoding = "utf-8"
        request.content_type = "application/json"

        serializer = HttpAnonymousRequestSerializer(request)
        print(serializer.data)
        # Output (example):
        # {
        #     'url': None,
        #     'method': 'GET',
        #     'GET': {'search': 'test'},
        #     'POST': {},
        #     'META': {},
        #     'path': '/api/v1/resource/',
        #     'encoding': 'utf-8',
        #     'content_type': 'application/json'
        # }

    .. note::
        The ``url`` field is computed from the request object if available. If the request does not
        provide a method for building the absolute URI, this field may be ``None``.

    .. warning::
        This serializer does not include user authentication information. For authenticated requests,
        use :class:`HttpAuthenticatedRequestSerializer`.
    """

    url = serializers.SerializerMethodField()
    method = serializers.ChoiceField(
        choices=[SmarterHttpMethods.GET, SmarterHttpMethods.POST, SmarterHttpMethods.PUT, SmarterHttpMethods.DELETE]
    )
    GET = serializers.DictField(child=serializers.CharField())
    POST = serializers.DictField(child=serializers.CharField())
    META = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    path = serializers.CharField()
    encoding = serializers.CharField()
    content_type = serializers.CharField()

    # pylint: disable=missing-class-docstring
    class Meta:
        fields = "__all__"
        extra_kwargs = {
            "url": {"required": False},
            "method": {"required": False},
            SmarterHttpMethods.GET: {"required": False},
            SmarterHttpMethods.POST: {"required": False},
            "path": {"required": False},
            "encoding": {"required": False},
            "content_type": {"required": False},
        }
        model = HttpRequest

    def to_representation(self, instance):
        """
        Serialize the request, adding its absolute ``url``.

        :param instance: The request.
        :returns: The serialized request.
        """
        ret = super().to_representation(instance)
        ret["url"] = self.get_url(instance)
        return ret

    def get_url(self, obj) -> Optional[str]:
        """
        Return the absolute url of ``obj.request``.

        :param obj: An object with a ``request`` attribute.
        :returns: The absolute url, or None if there is no request or it can't build one.
        """
        if not obj:
            return None
        request = getattr(obj, "request", None)
        if not request:
            return None
        if not hasattr(request, "build_absolute_uri"):
            return None
        url = request.build_absolute_uri()
        return url

    def get_META(self, obj) -> dict[str, str]:  # pylint: disable=invalid-name
        """
        Return the request's ``META``, limited to :data:`SAFE_META_KEYS`.

        :param obj: The request.
        :returns: The allowed keys and their values, as strings.
        """
        meta = getattr(obj, "META", None)
        if not isinstance(meta, dict):
            return {}
        safe_meta = {}
        for key in SAFE_META_KEYS:
            if key in meta:
                safe_meta[key] = str(meta[key])
        return safe_meta

    def get_body(self, obj: HttpRequest) -> JsonValue:
        """
        Return the request's body, parsed and with its credentials redacted.

        :param obj: The request.
        :returns: See :func:`serialize_body`.
        """
        return serialize_body(obj)

    def create(self, validated_data) -> HttpRequest:
        """
        Build a new, unsaved :class:`~django.http.HttpRequest` from the validated data.

        :param validated_data: The request attributes to set.
        :returns: The request.
        """
        req = HttpRequest()
        for attr, value in validated_data.items():
            setattr(req, attr, value)
        return req

    def update(self, instance: HttpRequest, validated_data):
        """
        Set the validated data's attributes on an existing request.

        :param instance: The request to change.
        :param validated_data: The request attributes to set.
        :returns: The same request.
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        return instance


class HttpAuthenticatedRequestSerializer(HttpAnonymousRequestSerializer):
    """
    Serializes authenticated HTTP request data for the Smarter API.

    This serializer extends :class:`HttpAnonymousRequestSerializer` to include user information,
    allowing for the representation of authenticated Django HTTP requests. It is intended for use
    in API endpoints, logging, or debugging where both request and user context are required.

    :param str url: The absolute URL of the request (read-only, derived from the request object).
    :param str method: The HTTP method (e.g., ``GET``, ``POST``, ``PUT``, ``DELETE``).
    :param dict GET: Query parameters from the request URL.
    :param dict POST: Data submitted in the body of a POST request.
    :param dict META: The request's headers and metadata, limited to :data:`SAFE_META_KEYS`.
    :param str path: The path portion of the request URL.
    :param str encoding: The encoding used for the request body.
    :param str content_type: The MIME type of the request body.
    :param user: The authenticated user making the request, serialized using :class:`UserSerializer`.

    **Example**

    .. code-block:: python

        from smarter.lib.django.http.serializers import HttpAuthenticatedRequestSerializer
        from django.http import HttpRequest
        from smarter.apps.account.models import User

        request = HttpRequest()
        request.method = "POST"
        request.path = "/api/v1/secure/"
        request.POST = {"data": "value"}
        request.encoding = "utf-8"
        request.content_type = "application/json"
        request.user = User(username="bob")

        serializer = HttpAuthenticatedRequestSerializer(request)
        print(serializer.data)
        # Output (example):
        # {
        #     'url': None,
        #     'method': 'POST',
        #     'GET': {},
        #     'POST': {'data': 'value'},
        #     'META': {},
        #     'path': '/api/v1/secure/',
        #     'encoding': 'utf-8',
        #     'content_type': 'application/json',
        #     'user': 'bob'
        # }

    .. note::
        The ``user`` field is serialized using :class:`UserSerializer` and only exposes the username by default.

    .. warning::
        Ensure that sensitive user information is not exposed by extending :class:`UserSerializer` with caution.
        This serializer should only be used in contexts where authenticated user data is appropriate.
    """

    user = UserSerializer()

    # pylint: disable=missing-class-docstring
    class Meta:
        fields = "__all__"
        read_only_fields = fields
        extra_kwargs = {
            "user": {"required": False},
        }
        model = HttpRequest

    def to_representation(self, instance):
        """
        Serialize the request, replacing the serialized ``user`` with its username.

        :param instance: The request.
        :returns: The serialized request.
        """
        ret = super().to_representation(instance)
        ret["user"] = ret["user"]["username"]
        return ret
