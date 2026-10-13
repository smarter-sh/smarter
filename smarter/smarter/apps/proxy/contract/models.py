"""
Pydantic models of the Proxies' REST api responses (``/api/v1/proxy/``).

The list of the Proxies that the caller may use is built from :class:`ProxyApiProxies`, with the
keys that the view built by hand before the api was modeled. A Proxy's passthrough
(``/api/v1/proxy/<name>/<path>``) forwards the request to the provider's api, and returns its
response, as it is, so its requests and responses are the provider's, not Smarter's, and are not modeled.
"""

from typing import TYPE_CHECKING

from pydantic import Field

from smarter.apps.account.contract.models import AccountApiModel

if TYPE_CHECKING:
    from django.http import HttpRequest

    from smarter.apps.proxy.models import Proxy


class ProxyApiProxy(AccountApiModel):
    """A Proxy that the caller may use: its name, provider and urls."""

    name: str = Field(..., description="The Proxy's name.")
    description: str | None = Field(None, description="MetaDataModel.description.")
    provider: str = Field(..., description="The name of its Provider.")
    url: str = Field(..., description="The Proxy's url: send the provider's requests here, with a Smarter api key.")
    upstream_url: str = Field(..., description="The provider's api, to which the Proxy forwards.")
    allowed_paths: list[str] = Field(..., description="Glob patterns of the paths that it forwards. Empty means all.")
    is_active: bool = Field(..., description="Whether it forwards requests.")

    @classmethod
    def from_model(cls, proxy: "Proxy", request: "HttpRequest") -> "ProxyApiProxy":
        """
        The contract's model of a Proxy.

        :param proxy: The row, whose ``provider`` should be fetched with it.
        :type proxy: smarter.apps.proxy.models.Proxy
        :param request: The request, whose host makes the Proxy's url absolute.
        :type request: django.http.HttpRequest
        :returns: The model.
        :rtype: ProxyApiProxy
        """
        return cls(
            name=proxy.name,
            description=proxy.description,
            provider=proxy.provider.name,
            url=request.build_absolute_uri(proxy.url),
            upstream_url=proxy.upstream_base_url,
            allowed_paths=proxy.allowed_paths or [],
            is_active=proxy.is_active,
        )


class ProxyApiProxies(AccountApiModel):
    """The Proxies that the caller may use, by name."""

    proxies: list[ProxyApiProxy]


PROXY_API_MODELS = (ProxyApiProxies,)
"""The models whose JSON Schemas the Smarter api's OpenAPI document includes."""

__all__ = ["PROXY_API_MODELS", "ProxyApiProxies", "ProxyApiProxy"]
