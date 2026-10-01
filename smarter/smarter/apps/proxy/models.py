"""
Proxy: passthrough access to a 3rd party LLM provider's API, with an API key that Smarter keeps.

A Proxy forwards requests, as they are, to an LLM provider's native API, e.g.
``https://api.openai.com/v1/``. The only difference between calling the provider directly
and calling it through a Proxy is the API key: the caller authenticates with a Smarter API
key, and Smarter adds the provider's API key, which it keeps in a
:class:`~smarter.apps.secret.models.Secret`. The provider's API key never leaves Smarter.

.. code-block:: text

    client --(Smarter API key)--> /api/v1/proxy/<name>/<path> --(provider API key)--> <base_url><path>

A Proxy is configured by a Proxy manifest. See
:mod:`smarter.apps.proxy.manifest.models.proxy.spec`.

Like other Smarter resources, a Proxy is owned by a user, and its visibility is
determined by ownership and role: the built-in Proxies are owned by the Smarter admin,
so every account may use them.
"""

import fnmatch
from typing import Optional
from urllib.parse import urlparse

from django.db import models
from django.urls import NoReverseMatch, reverse

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
    MetaDataWithOwnershipModelManager,
)
from smarter.apps.provider.models import Provider
from smarter.apps.secret.models import Secret
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .const import DEFAULT_AUTH_HEADER, DEFAULT_AUTH_SCHEME, DEFAULT_TIMEOUT

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PROXY_LOGGING])


def normalize_path(path: Optional[str]) -> Optional[str]:
    """
    Normalize a path within a Proxy's base URL, e.g. ``/chat/completions`` to ``chat/completions``.

    The path is relative to the base URL, so its leading slashes are removed. Paths that could
    leave the base URL are refused: ``..`` and ``.`` segments, empty segments, backslashes, and
    absolute URLs.

    :returns: The normalized path, or ``None`` if it is refused.
    """
    path = (path or "").lstrip("/")
    if not path:
        return ""
    if "\\" in path or "://" in path or "%2e" in path.lower() or "%2f" in path.lower():
        return None
    segments = path.split("/")
    # a trailing slash is allowed, e.g. models/, but no other empty segments.
    if any(segment in ("", ".", "..") for segment in segments[:-1]) or segments[-1] in (".", ".."):
        return None
    return path


class Proxy(MetaDataWithOwnershipModel):
    """
    A Proxy of a 3rd party LLM provider's API.

    :param provider: The Provider whose API the Proxy forwards to.
    :param api_key_secret: The Secret that contains the provider's API key. If ``None``, the
        Provider's own API key Secret is used.
    :param base_url: The base URL of the provider's API. If empty, the Provider's base URL is used.
    :param auth_header: The HTTP header in which the provider expects its API key, e.g.
        ``Authorization`` or ``x-api-key``.
    :param auth_scheme: The prefix of the API key in the header, e.g. ``Bearer``, or empty for none.
    :param headers: Other HTTP headers that are added to every request, e.g.
        ``{"anthropic-version": "2023-06-01"}``.
    :param allowed_paths: The paths, relative to the base URL, that callers may use, as glob
        patterns, e.g. ``["chat/completions", "models/*"]``. Empty allows every path.
    :param timeout: The most seconds to wait for the provider's response.
    :param is_active: Inactive Proxies refuse every request.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name = "Proxy"
        verbose_name_plural = "Proxies"
        unique_together = ("user_profile", "name")

    objects: MetaDataWithOwnershipModelManager["Proxy"] = MetaDataWithOwnershipModelManager()

    provider = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        related_name="proxies",
        help_text="The provider whose API this proxy forwards requests to.",
    )
    api_key_secret = models.ForeignKey(
        Secret,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="proxies",
        help_text="The secret containing the provider's API key. If empty, the provider's own API key is used.",
    )
    base_url = models.URLField(
        max_length=255,
        blank=True,
        default="",
        help_text="The base URL of the provider's API, e.g. https://api.openai.com/v1/. If empty, the provider's base URL is used.",
    )
    auth_header = models.CharField(
        max_length=64,
        default=DEFAULT_AUTH_HEADER,
        help_text="The HTTP header in which the provider expects its API key, e.g. 'Authorization' or 'x-api-key'.",
    )
    auth_scheme = models.CharField(
        max_length=32,
        blank=True,
        default=DEFAULT_AUTH_SCHEME,
        help_text="The prefix of the API key in the auth header, e.g. 'Bearer'. Empty for none.",
    )
    headers = models.JSONField(
        default=dict,
        blank=True,
        help_text="Other HTTP headers that are added to every request, e.g. {'anthropic-version': '2023-06-01'}.",
    )
    allowed_paths = models.JSONField(
        default=list,
        blank=True,
        help_text="Glob patterns of the paths, relative to the base URL, that callers may use. Empty allows every path.",
    )
    timeout = models.PositiveIntegerField(
        default=DEFAULT_TIMEOUT,
        help_text="The most seconds to wait for the provider's response.",
    )
    is_active = models.BooleanField(default=True, help_text="Inactive proxies refuse every request.")

    def __str__(self) -> str:
        return f"{self.name}"

    @property
    def is_billable_resource(self) -> bool:
        """
        Proxies are billable: each request is charged to the Proxy, and to the caller.

        :returns: True
        :rtype: bool
        """
        return True

    @property
    def upstream_base_url(self) -> str:
        """
        The base URL of the provider's API, with a trailing slash: :attr:`base_url`, else the Provider's.

        :returns: The base URL, or an empty string if neither is set.
        """
        url = self.base_url or (self.provider.base_url if self.provider_id else "") or ""  # type: ignore[attr-defined]
        if url and not url.endswith("/"):
            url += "/"
        return url

    @property
    def upstream_host(self) -> str:
        """The host name of the provider's API, e.g. ``api.openai.com``."""
        return urlparse(self.upstream_base_url).hostname or ""

    @property
    def secret(self) -> Optional[Secret]:
        """The Secret that contains the provider's API key: :attr:`api_key_secret`, else the Provider's."""
        if self.api_key_secret_id:  # type: ignore[attr-defined]
            return self.api_key_secret
        if self.provider_id and self.provider.api_key_id:  # type: ignore[attr-defined]
            return self.provider.api_key
        return None

    def may_use_secret(self, secret: Optional[Secret]) -> bool:
        """
        Whether the Proxy may send a Secret's API key: only if the Secret belongs to the Proxy owner's account.

        Otherwise anyone could write a Proxy that sends another account's API key, e.g. the
        platform's, to a base URL of their choosing. The built-in Proxies, which the Smarter admin
        owns, may use the platform's Secrets, and every account may use them.
        """
        if secret is None:
            return False
        return secret.user_profile.account_id == self.user_profile.account_id  # type: ignore[attr-defined]

    @property
    def secret_name(self) -> Optional[str]:
        """The name of :attr:`secret`, never its value."""
        secret = self.secret
        return secret.name if secret else None

    def upstream_url(self, path: str) -> Optional[str]:
        """
        The provider's URL of a path, relative to the base URL.

        :returns: The URL, or ``None`` if the path is refused by :func:`normalize_path`.
        """
        normalized = normalize_path(path)
        if normalized is None:
            return None
        return self.upstream_base_url + normalized

    def is_path_allowed(self, path: str) -> bool:
        """
        Whether callers may use a path: it is a valid path, and :attr:`allowed_paths` is empty or a pattern matches it.

        The patterns are matched with :func:`fnmatch.fnmatchcase`, so ``*`` also matches ``/``,
        e.g. ``models/*`` matches ``models/gemini-2.5-flash:generateContent``. A trailing
        slash is ignored.
        """
        normalized = normalize_path(path)
        if normalized is None:
            return False
        if not self.allowed_paths:
            return True
        normalized = normalized.rstrip("/")
        patterns = list(self.allowed_paths or [])
        return any(fnmatch.fnmatchcase(normalized, str(pattern).strip("/")) for pattern in patterns)

    def auth_header_value(self, api_key: str) -> str:
        """The value of :attr:`auth_header`, e.g. ``Bearer sk-...``."""
        return f"{self.auth_scheme} {api_key}" if self.auth_scheme else api_key

    @property
    def url(self) -> str:
        """
        The path of the Proxy's passthrough endpoint, e.g. ``/api/v1/proxy/openai/``.

        Empty if the endpoints are disabled, with ``SMARTER_ENABLE_PROXY=false``.
        """
        # pylint: disable=C0415
        from smarter.apps.proxy.api.v1.urls import ProxyApiV1ReverseViews

        try:
            return reverse(
                f"{ProxyApiV1ReverseViews.namespace}:{ProxyApiV1ReverseViews.passthrough_root}",
                kwargs={"name": self.name},
            )
        except NoReverseMatch:
            return ""

    @property
    def manifest_url(self) -> str:
        """The URL of the Proxy's detail view in the web console, which renders its manifest."""
        # pylint: disable=C0415
        from smarter.apps.proxy.urls import ProxyReverseNames

        return reverse(
            f"{ProxyReverseNames.namespace}:{ProxyReverseNames.detailview}",
            kwargs={"hashed_id": self.hashed_id},  # type: ignore[attr-defined]
        )


__all__ = [
    "Proxy",
    "normalize_path",
]
