"""
The page that a browser sees at a deployed LLMClient's endpoints.

A deployed LLMClient's endpoints, ``/config/`` and ``/prompt/``, are api endpoints that answer only POST.
A browser that opens one of them, or the LLMClient's default url, instead receives a page about the
LLMClient and The Smarter Project: the curl commands that call the endpoints, the LLMClient's
manifest, without the personal information in it, and how to build one. The page is served only while
the ``enable_llmclient_endpoints_page`` waffle switch is active.

.. seealso::

    - :mod:`smarter.urls.llmclients`
    - :mod:`smarter.urls.console`, which serves LLMClients on their custom domains
"""

import re
from functools import wraps
from typing import Callable, Optional

import yaml
from django.http import HttpRequest, HttpResponse
from django.http.response import HttpResponseBase
from django.shortcuts import render
from django.utils.html import escape
from django.utils.safestring import SafeString, mark_safe

from smarter.apps.llmclient.manifest.models.llmclient.const import MANIFEST_KIND
from smarter.apps.llmclient.manifest.models.llmclient.model import SAMLLMClient
from smarter.apps.llmclient.models import LLMClient, get_cached_llmclient_by_request
from smarter.apps.prompt.contract.models import (
    PromptChatApiMessage,
    PromptChatApiPromptRequest,
)
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.http.shortcuts import SmarterHttpResponseNotFound
from smarter.lib.django.views import SmarterWebHtmlView
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])

EXAMPLE_PROMPT = "hello world"
"""The prompt that the page's example ``/prompt/`` command sends."""

BROWSER_METHODS = ("GET", "HEAD")
"""The methods that :func:`browser_friendly` sends to :class:`LLMClientEndpointsView`."""

MANIFEST_PII_EXCLUDE = {"status": {"username"}}
"""
The fields that :func:`manifest_yaml` leaves out of the page's manifest: the personal information in it.

``status.username`` is the owner's username.
"""

MANIFEST_CACHE_TIMEOUT = 600
"""How long, in seconds, :func:`cached_manifest_yaml` keeps a manifest."""

YAML_KEY_LINE = re.compile(r"^(?P<indent>\s*)(?P<dash>- )?(?P<key>[A-Za-z_][\w-]*)(?P<colon>:)(?P<value>.*)$")
"""A YAML line that starts a mapping key, optionally as a list item: ``  - key: value``."""

YAML_LIST_LINE = re.compile(r"^(?P<indent>\s*)(?P<dash>- )(?P<value>.*)$")
"""A YAML line that is a list item's scalar: ``  - value``."""

YAML_LITERAL_VALUES = ("true", "false", "null", "~")
"""The YAML scalars that :func:`highlight_yaml` colors as literals."""


def curl_command(url: str, body: str = "", authenticated: bool = False) -> str:
    """
    A curl command that POSTs to a deployed LLMClient's endpoint, one option per line.

    :param url: The endpoint's url.
    :type url: str
    :param body: The JSON request body, or empty for none. It must not contain a single quote.
    :type body: str
    :param authenticated: True to send an api key, which an LLMClient with api keys requires.
    :type authenticated: bool
    :returns: The command.
    :rtype: str
    """
    lines = [f"curl -X POST {url}", '-H "Content-Type: application/json"']
    if authenticated:
        lines.append('-H "Authorization: Token <YOUR-API-KEY>"')
    if body:
        lines.append(f"-d '{body}'")
    return " \\\n  ".join(lines)


def llmclient_manifest(llmclient: LLMClient) -> SAMLLMClient:
    """
    The LLMClient's manifest, as ``smarter describe llmclient`` returns it, from its broker.

    :param llmclient: The LLMClient.
    :type llmclient: smarter.apps.llmclient.models.LLMClient
    :returns: The manifest.
    :rtype: smarter.apps.llmclient.manifest.models.llmclient.model.SAMLLMClient
    :raises SAMLLMClientBrokerError: If the broker can't build it.
    """
    # pylint: disable=C0415
    from smarter.apps.llmclient.manifest.brokers.llmclient import (
        SAMLLMClientBroker,
        SAMLLMClientBrokerError,
    )

    broker = SAMLLMClientBroker(None, name=llmclient.name, kind=MANIFEST_KIND, user_profile=llmclient.user_profile)
    data = broker.django_orm_to_manifest_dict()
    if data is None:
        raise SAMLLMClientBrokerError(f"The manifest of {llmclient} could not be built.", thing=MANIFEST_KIND)
    return SAMLLMClient.model_validate(data)


class _ManifestDumper(yaml.SafeDumper):
    """A YAML dumper that writes multi-line strings, e.g. a system prompt, as literal blocks."""


def _represent_str(dumper: yaml.SafeDumper, value: str) -> yaml.ScalarNode:
    style = "|" if "\n" in value else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


_ManifestDumper.add_representer(str, _represent_str)


def manifest_yaml(manifest: SAMLLMClient) -> str:
    """
    The manifest as YAML, in the order of its model's fields, without :data:`MANIFEST_PII_EXCLUDE`.

    :param manifest: The manifest.
    :type manifest: smarter.apps.llmclient.manifest.models.llmclient.model.SAMLLMClient
    :returns: The YAML.
    :rtype: str
    """
    data = manifest.model_dump(mode="json", exclude_none=True, exclude=MANIFEST_PII_EXCLUDE)
    return yaml.dump(data, Dumper=_ManifestDumper, sort_keys=False, allow_unicode=True, width=100)


@cache_results(timeout=MANIFEST_CACHE_TIMEOUT)
def cached_manifest_yaml(llmclient_id: int, updated_at: str) -> str:
    """
    The YAML of an LLMClient's manifest, for the page, which its broker takes about a second to build.

    An update of the LLMClient changes ``updated_at``, and so the key. A change to a resource that it
    refers to, e.g. a plugin added to it, shows after :data:`MANIFEST_CACHE_TIMEOUT`.

    :param llmclient_id: The LLMClient's id.
    :type llmclient_id: int
    :param updated_at: The LLMClient's ``updated_at``, in ISO 8601.
    :type updated_at: str
    :returns: The YAML.
    :rtype: str
    :raises SAMLLMClientBrokerError: If the broker can't build the manifest, which is then not cached.
    """
    return manifest_yaml(llmclient_manifest(LLMClient.objects.get(pk=llmclient_id)))


def _yaml_value(value: str) -> str:
    """The HTML of a YAML scalar, with a class for its kind."""
    stripped = value.strip()
    if not stripped:
        return escape(value)
    if stripped in YAML_LITERAL_VALUES or re.fullmatch(r"-?\d+(\.\d+)?", stripped):
        css_class = "yaml-literal"
    elif stripped.startswith(("|", ">")):
        css_class = "yaml-block"
    else:
        css_class = "yaml-string"
    return f'{escape(value[: len(value) - len(value.lstrip())])}<span class="{css_class}">{escape(stripped)}</span>'


def highlight_yaml(text: str) -> SafeString:
    """
    YAML, as HTML whose spans color its keys, strings, literals and literal blocks.

    Every part of the text is escaped. The spans' classes are ``yaml-key``, ``yaml-string``,
    ``yaml-literal``, ``yaml-block`` and ``yaml-punctuation``, which the page styles.

    :param text: The YAML.
    :type text: str
    :returns: The HTML, for a ``<pre>``.
    :rtype: django.utils.safestring.SafeString
    """
    lines: list[str] = []
    block_indent: Optional[int] = None
    for line in text.splitlines():
        indent = len(line) - len(line.lstrip())
        if block_indent is not None and (not line.strip() or indent > block_indent):
            lines.append(f'<span class="yaml-string">{escape(line)}</span>')
            continue
        block_indent = None
        key_line = YAML_KEY_LINE.match(line)
        list_line = YAML_LIST_LINE.match(line)
        if key_line:
            dash = '<span class="yaml-punctuation">- </span>' if key_line["dash"] else ""
            lines.append(
                f'{key_line["indent"]}{dash}<span class="yaml-key">{escape(key_line["key"])}</span>'
                f'<span class="yaml-punctuation">:</span>{_yaml_value(key_line["value"])}'
            )
            if key_line["value"].strip().startswith(("|", ">")):
                block_indent = indent + (2 if key_line["dash"] else 0)
        elif list_line:
            lines.append(
                f'{list_line["indent"]}<span class="yaml-punctuation">- </span>{_yaml_value(list_line["value"])}'
            )
        else:
            lines.append(escape(line))
    return mark_safe("\n".join(lines))  # nosec B308 B703: every part of every line is escaped.


class LLMClientEndpointsView(SmarterWebHtmlView):
    """
    A deployed LLMClient's endpoints, for a browser, and The Smarter Project, which built it.

    A host that serves no deployed LLMClient is a 404, as it is for the endpoints themselves.
    """

    template_path = "llmclient/endpoints.html"

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this view."""
        class_name = f"{__name__}.{LLMClientEndpointsView.__name__}[{id(self)}]"
        return logging.formatted_text(class_name)

    def get(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        """
        The page, for the LLMClient that serves the request's host.

        :param request: The request.
        :type request: django.http.HttpRequest
        :returns: The page, or a 404 if no deployed LLMClient serves the host.
        :rtype: django.http.HttpResponse
        """
        llmclient: Optional[LLMClient] = get_cached_llmclient_by_request(request=request)
        if llmclient is None or not llmclient.deployed:
            logger.debug(
                "%s.get() no deployed LLMClient serves %s", self.formatted_class_name, request.build_absolute_uri()
            )
            return SmarterHttpResponseNotFound(request=request, error_message="LLMClient not found.")

        base_url = llmclient.url.rstrip("/")
        authenticated = llmclient.is_authentication_required
        prompt = PromptChatApiPromptRequest(messages=[PromptChatApiMessage(role="user", content=EXAMPLE_PROMPT)])
        manifest: Optional[str] = None
        try:
            manifest = cached_manifest_yaml(llmclient.pk, llmclient.updated_at.isoformat())
        # the page, without the manifest, rather than an error. pylint: disable=W0718
        except Exception as e:
            logger.warning("%s.get() could not build the manifest of %s: %s", self.formatted_class_name, llmclient, e)
        context = {
            "llmclient": {
                "name": llmclient.name,
                "app_name": llmclient.app_name or llmclient.name,
                "description": llmclient.description,
                "welcome_message": llmclient.app_welcome_message,
                "example_prompts": llmclient.app_example_prompts or [],
                "provider": llmclient.provider,
                "model": llmclient.default_model,
                "version": llmclient.version,
                "url": base_url,
                "is_custom_domain": bool(llmclient.custom_host),
            },
            "authenticated": authenticated,
            "config_command": curl_command(f"{base_url}/config/", authenticated=authenticated),
            "prompt_command": curl_command(
                f"{base_url}/prompt/",
                body=prompt.model_dump_json(exclude_none=True),
                authenticated=authenticated,
            ),
            "manifest_html": highlight_yaml(manifest) if manifest else None,
            "deploy_commands": f"smarter apply -f {llmclient.name}.yaml\nsmarter deploy llmclient {llmclient.name}",
        }
        logger.debug("%s.get() endpoints page for %s", self.formatted_class_name, llmclient)
        # rendered as is, not minified: the minifier drops whitespace-only text, which is the indentation
        # between the highlighted spans of the manifest's YAML.
        return render(request=request, template_name=self.template_path, context=context)


def browser_friendly(api_view: Callable[..., HttpResponseBase]) -> Callable[..., HttpResponseBase]:
    """
    Wrap a deployed LLMClient's api view, so that a GET or HEAD receives :class:`LLMClientEndpointsView`.

    Only while the ``enable_llmclient_endpoints_page`` switch is active. Every other request, including a
    GET while it is inactive, goes to the api view. The wrapper keeps the api view's attributes, e.g. ``csrf_exempt``.

    .. code-block:: python

        path("prompt/", browser_friendly(DefaultLLMClientApiView.as_view())),

    :param api_view: The api view, from ``as_view()``.
    :type api_view: Callable[..., django.http.response.HttpResponseBase]
    :returns: The wrapped view.
    :rtype: Callable[..., django.http.response.HttpResponseBase]
    """
    endpoints_view = LLMClientEndpointsView.as_view()

    @wraps(api_view)
    def view(request: HttpRequest, *args, **kwargs) -> HttpResponseBase:
        if request.method in BROWSER_METHODS and waffle.switch_is_active(
            SmarterWaffleSwitches.ENABLE_LLMCLIENT_ENDPOINTS_PAGE
        ):
            return endpoints_view(request, *args, **kwargs)
        return api_view(request, *args, **kwargs)

    return view
